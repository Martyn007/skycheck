from django.db import models
from django.contrib.auth.models import User


class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    city_name = models.CharField(max_length=100)
    searched_at = models.DateTimeField(auto_now_add=True)
    temperature = models.FloatField(null=True, blank=True)
    description = models.CharField(max_length=200, null=True, blank=True)
    country = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return f"{self.city_name} ({self.searched_at.strftime('%Y-%m-%d %H:%M')})"

    class Meta:
        ordering = ['-searched_at']
        verbose_name_plural = "Search Histories"


class FavoriteCity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    city_name = models.CharField(max_length=100)
    country = models.CharField(max_length=10, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} → {self.city_name}"

    class Meta:
        unique_together = ('user', 'city_name')
        ordering = ['city_name']
