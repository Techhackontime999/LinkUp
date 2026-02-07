from django.urls import path
from .admin_views import SeedTestDataView, ClearTestDataView, TestDataStatsView

app_name = 'admin'

urlpatterns = [
    path('seed-test-data/', SeedTestDataView.as_view(), name='seed_test_data'),
    path('clear-test-data/', ClearTestDataView.as_view(), name='clear_test_data'),
    path('test-data-stats/', TestDataStatsView.as_view(), name='test_data_stats'),
]
