from django.urls import path

from .views import petlistings_list_and_create_view, petlistings_category_list_view, petlisting_detail_view, petlisting_photo_view

app_name = 'petlistings'

urlpatterns = [
    path('', petlistings_list_and_create_view, name='petlisting-lists'),
    path('/filter', petlistings_category_list_view, name='petlisting-category-lists'),
    path('/<int:pet_id>', petlisting_detail_view, name='pelisting-detail'),
    path('/<int:pet_id>/<int:photo_id>', petlisting_photo_view, name='petlisting-photo')
]