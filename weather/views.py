import requests
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings

from .models import SearchHistory, FavoriteCity
from .forms import RegisterForm, LoginForm


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def get_weather_emoji(description):
    d = description.lower()
    if 'clear' in d or 'sunny' in d:    return '☀️'
    elif 'cloud' in d:                  return '☁️'
    elif 'rain' in d or 'drizzle' in d: return '🌧️'
    elif 'thunder' in d or 'storm' in d:return '⛈️'
    elif 'snow' in d:                   return '❄️'
    elif 'mist' in d or 'fog' in d:     return '🌫️'
    else:                               return '🌤️'


def fetch_current_weather(city, api_key):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url, timeout=10)
    return response


def fetch_forecast(city, api_key):
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&cnt=40"
    response = requests.get(url, timeout=10)
    return response


def parse_forecast(data):
    """
    Parse 5-day / 3-hour forecast into:
    - daily_forecast: list of 5 days with high/low/desc/icon
    - chart_labels: hourly labels for next 24 hours (8 points)
    - chart_temps: matching temperatures
    """
    from collections import defaultdict
    import datetime

    daily = defaultdict(lambda: {'temps': [], 'icons': [], 'descs': []})
    chart_labels = []
    chart_temps = []
    chart_humidity = []
    chart_wind = []

    for item in data['list']:
        dt = datetime.datetime.fromtimestamp(item['dt'])
        day_key = dt.strftime('%A, %b %d')
        daily[day_key]['temps'].append(item['main']['temp'])
        daily[day_key]['icons'].append(item['weather'][0]['icon'])
        daily[day_key]['descs'].append(item['weather'][0]['description'])

    # Chart: next 8 x 3hr slots = 24 hours
    for item in data['list'][:8]:
        dt = datetime.datetime.fromtimestamp(item['dt'])
        chart_labels.append(dt.strftime('%I %p'))
        chart_temps.append(round(item['main']['temp'], 1))
        chart_humidity.append(item['main']['humidity'])
        chart_wind.append(round(item['wind']['speed'] * 3.6, 1))

    # Build 5-day summary
    daily_forecast = []
    for day_key, vals in list(daily.items())[:5]:
        high = round(max(vals['temps']))
        low  = round(min(vals['temps']))
        desc = vals['descs'][len(vals['descs']) // 2].title()
        icon = vals['icons'][len(vals['icons']) // 2]
        daily_forecast.append({
            'day':   day_key,
            'high':  high,
            'low':   low,
            'desc':  desc,
            'icon':  f"https://openweathermap.org/img/wn/{icon}@2x.png",
            'emoji': get_weather_emoji(desc),
        })

    return {
        'daily': daily_forecast,
        'chart_labels':   chart_labels,
        'chart_temps':    chart_temps,
        'chart_humidity': chart_humidity,
        'chart_wind':     chart_wind,
    }


# ──────────────────────────────────────────────
# Auth Views
# ──────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to SkyCheck, {user.username}! 🎉")
        return redirect('home')
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"Welcome back, {user.username}! ☀️")
        return redirect('home')
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You've been logged out. See you soon!")
    return redirect('login')


# ──────────────────────────────────────────────
# Favorites (AJAX)
# ──────────────────────────────────────────────

@login_required
def toggle_favorite(request):
    if request.method == 'POST':
        city = request.POST.get('city', '').strip()
        country = request.POST.get('country', '').strip()
        if not city:
            return JsonResponse({'error': 'No city provided'}, status=400)

        fav, created = FavoriteCity.objects.get_or_create(
            user=request.user,
            city_name=city,
            defaults={'country': country}
        )
        if not created:
            fav.delete()
            return JsonResponse({'status': 'removed', 'city': city})
        return JsonResponse({'status': 'added', 'city': city})
    return JsonResponse({'error': 'Invalid method'}, status=405)


@login_required
def favorites_view(request):
    favorites = FavoriteCity.objects.filter(user=request.user)
    return render(request, 'favorites.html', {'favorites': favorites})


# ──────────────────────────────────────────────
# Main Home View
# ──────────────────────────────────────────────

def home(request):
    weather_data  = None
    forecast_data = None
    error_message = None
    is_favorite   = False

    recent_searches = SearchHistory.objects.filter(
        user=request.user if request.user.is_authenticated else None
    )[:5] if request.user.is_authenticated else SearchHistory.objects.filter(user=None)[:5]

    if request.method == 'POST':
        city = request.POST.get('city', '').strip()
        if not city:
            error_message = "Please enter a city name."
        else:
            api_key = settings.OPENWEATHER_API_KEY
            try:
                # Current weather
                resp = fetch_current_weather(city, api_key)
                data = resp.json()

                if resp.status_code == 200:
                    desc = data['weather'][0]['description']
                    weather_data = {
                        'city':        data['name'],
                        'country':     data['sys']['country'],
                        'temperature': round(data['main']['temp']),
                        'feels_like':  round(data['main']['feels_like']),
                        'temp_min':    round(data['main']['temp_min']),
                        'temp_max':    round(data['main']['temp_max']),
                        'description': desc.title(),
                        'icon':        f"https://openweathermap.org/img/wn/{data['weather'][0]['icon']}@2x.png",
                        'emoji':       get_weather_emoji(desc),
                        'humidity':    data['main']['humidity'],
                        'wind_speed':  round(data['wind']['speed'] * 3.6, 1),
                        'pressure':    data['main']['pressure'],
                        'visibility':  round(data.get('visibility', 0) / 1000, 1),
                        'clouds':      data['clouds']['all'],
                    }

                    # 5-day forecast
                    fc_resp = fetch_forecast(data['name'], api_key)
                    if fc_resp.status_code == 200:
                        forecast_data = parse_forecast(fc_resp.json())

                    # Save history
                    SearchHistory.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        city_name=data['name'],
                        temperature=weather_data['temperature'],
                        description=desc,
                        country=data['sys']['country'],
                    )

                    # Check favorite
                    if request.user.is_authenticated:
                        is_favorite = FavoriteCity.objects.filter(
                            user=request.user, city_name=data['name']
                        ).exists()

                    recent_searches = SearchHistory.objects.filter(
                        user=request.user if request.user.is_authenticated else None
                    )[:5]

                elif resp.status_code == 404:
                    error_message = f"City '{city}' not found. Check the spelling and try again."
                elif resp.status_code == 401:
                    error_message = "Invalid API key. Please check your settings.py."
                else:
                    error_message = "Could not fetch weather data. Please try again."

            except requests.exceptions.ConnectionError:
                error_message = "Network error. Check your internet connection."
            except requests.exceptions.Timeout:
                error_message = "Request timed out. Please try again."
            except Exception as e:
                error_message = f"Unexpected error: {str(e)}"

    context = {
        'weather_data':  weather_data,
        'forecast_data': forecast_data,
        'error_message': error_message,
        'recent_searches': recent_searches,
        'is_favorite':   is_favorite,
    }
    return render(request, 'home.html', context)
