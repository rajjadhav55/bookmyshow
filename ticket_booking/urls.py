from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .auth_views import MyTokenObtainPairView
from .views import generate_invoice_pdf

urlpatterns = [
    path('', views.movie_list, name='movies'),
    path('explore/', views.explore, name='explore'),
    path('genre/',views.genre_list, name = 'genres'),
    path('payment/', views.payment , name = "payment"),
    path('movies/', views.movie_list, name='movie_list'),
    path('language/',views.language_list, name='language'),
    path('booking/', views.initial_booking, name='book_ticket'),
    path('register_user/', views.register_user, name='register' ),
    path('booking_info/', views.booking_info, name="booking_info" ),
    path('seat_layout/', views.show_seat_layout, name='show_seat_layout'),
    path('theater_list/', views.theater_list, name='theater_list_by_movie'),
    path('payment_confirm/', views.payment_confirm , name = "payment_confirm"),
    path('api/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('retrieve_movie/<int:movie_id>', views.retrieve_movie, name='retrive_movie'),
    path('invoice/<int:booking_id>/', views.generate_invoice_pdf, name='invoice_view' ),
    path('download-invoice/<int:booking_id>/', generate_invoice_pdf, name='download_invoice'),

    # path('movie_list/', views.movie_list_with_status, name='movie_list_with_status'),
    # path('mybookings/', views.my_bookings, name='my_bookings '),
    # path('theaters/', views.theater_list, name='theater list'),
    # path('lock_seats/', views.lock_seats, name='lock_seats'),
    # path('login_user/',views.login_user,name="login"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
