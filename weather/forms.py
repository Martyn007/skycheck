from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'your@email.com',
            'class': 'auth-input',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': 'Choose a username',
            'password1': 'Create a password',
            'password2': 'Confirm your password',
        }
        for field_name, ph in placeholders.items():
            self.fields[field_name].widget.attrs.update({
                'placeholder': ph,
                'class': 'auth-input',
            })
            self.fields[field_name].help_text = None

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Username',
            'class': 'auth-input',
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Password',
            'class': 'auth-input',
        })
