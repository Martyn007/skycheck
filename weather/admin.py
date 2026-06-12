from django.contrib import admin
from .models import SearchHistory, FavoriteCity


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ('city_name', 'country', 'temperature', 'description', 'user', 'searched_at')
    list_filter  = ('country', 'searched_at')
    search_fields = ('city_name', 'user__username')
    readonly_fields = ('searched_at',)
    ordering = ('-searched_at',)


@admin.register(FavoriteCity)
class FavoriteCityAdmin(admin.ModelAdmin):
    list_display  = ('user', 'city_name', 'country', 'added_at')
    list_filter   = ('country',)
    search_fields = ('city_name', 'user__username')
    ordering      = ('user', 'city_name')
