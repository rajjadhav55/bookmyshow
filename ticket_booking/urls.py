from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .auth_views import MyTokenObtainPairView

urlpatterns = [
    path('api/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login_user/',views.login_user,name="login"),
    path('register_user/', views.register_user, name='register'),
    path('movies/', views.movie_list, name='movie list'),
    # path('theaters/', views.theater_list, name='theater list'),
    path('payment_confirm/', views.payment_confirm , name = "payment_confirm"),
    path('payment/', views.payment , name = "payment"),
    path('', views.movie_list, name='movies'),
    path('explore/', views.explore, name='explore'),
    path('theater_list/', views.theater_list, name='theater_list_by_movie'),
    path('booking/', views.initial_booking, name='book_ticket'),
    # path('movie_list/', views.movie_list_with_status, name='movie_list_with_status'),
    path('seat_layout/', views.show_seat_layout, name='show_seat_layout'),
    # path('lock_seats/', views.lock_seats, name='lock_seats'),
    path('retrieve_movie/<int:movie_id>', views.retrieve_movie, name='retrive_movie'),
    path('booking_info/', views.booking_info,name="booking_info")
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#b8e21e5a-5de7-46e7-83d5-5924f4f1f2ca