from django.contrib import admin
from .models import Movie, Theater, Show, Seat, Bookinginfo , Genre, Language , State , City , ShowSeatBooking ,Session
from django.utils.html import format_html

class TheaterAdmin(admin.ModelAdmin):
    list_display = ('id','name','location','city__name','city__state__name')
    search_fields = ('name',)

    

class StateAdmine(admin.ModelAdmin):
    list_display = ('name',)

class CityAdmine(admin.ModelAdmin):
    list_display = ('name','state',)

class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'duration_min', 'release_date', 'get_genres','get_lang','image_tag',)
    search_fields = ('title',)

    
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="80" height="100" />', obj.image.url)
        return "-"
    image_tag.short_description = 'Poster'

    def get_genres(self, obj):
        return ", ".join(genre.name for genre in obj.genres.all())
    get_genres.short_description = 'Genres'

    def get_lang(self, obj):
        return ", ".join(lang.name for lang in obj.language.all())
    get_genres.short_description = 'Genres'

class GenreAdmine (admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class LanguageAmine (admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


# Custom method added to ShowAdmin to calculate available seats
class ShowAdmin(admin.ModelAdmin):
    list_display = ("id",'movie','language', 'theater', 'theater__location','theater__city__name','time_slot',)
    list_filter = ('theater', 'time_slot')
    search_fields = ('movie__title', 'theater__name')

    # def seats_available(self, obj):
    #     return obj.seats.filter(is_booked=False).count()
    # seats_available.short_description = 'Available Seats'

class SeatAdmin(admin.ModelAdmin):
    list_display = ('id','seat_number', 'theater__name', )
    # list_filter = ('is_booked',)


class BookinginfoAdmin(admin.ModelAdmin):
    list_display = ('user', 'booking_time', 'number_of_tickets','theater','is_paid','show',"get_seats")
    # filter_horizontal = ('seats',)
    def get_seats(self, obj):
        return ", ".join(seat.seat_number for seat in obj.seats.all())
    get_seats.short_description = 'seat'

class ShowSeatBookingAdmin(admin.ModelAdmin):
    list_display =('show','seat','bookinginfo',)

class SessionAdmin(admin.ModelAdmin):
    list_display = ('user','session_id','created_at')








admin.site.register(Theater, TheaterAdmin)
admin.site.register(Movie, MovieAdmin)
admin.site.register(Show, ShowAdmin)
admin.site.register(Seat, SeatAdmin)
admin.site.register(Bookinginfo, BookinginfoAdmin)
admin.site.register(Genre, GenreAdmine)
admin.site.register(Language, LanguageAmine)
admin.site.register(State, StateAdmine)
admin.site.register(City, CityAdmine)
admin.site.register(ShowSeatBooking,ShowSeatBookingAdmin)
admin.site.register(Session,SessionAdmin)