from datetime import datetime
from django.utils import timezone
from django.contrib.auth import get_user_model
import json , uuid
from .models import Theater , Movie , Show , Bookinginfo , Genre , Language ,Seat ,ShowSeatBooking, customUser, Session
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Min , F
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models.functions import JSONObject
from datetime import timedelta
from django.db import transaction
from django.contrib.auth import authenticate, login, logout
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
# from .utils import generate_jwt 
# 


User = get_user_model() 

@csrf_exempt 
@require_http_methods(["POST"])
def register_user(request):
    try:
        data = json.loads(request.body)
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        contact_no = data.get("contact_no","")
        is_staff = data.get("is_staff","False")
        is_admin = data.get("is_admin","False")


        if not username or not password or not email:
            return JsonResponse({"error": "Username, email, and password are required"}, status=400)
        
        user = User.objects.all()
        if  not contact_no.isdigit():
            return JsonResponse("contact number should be number only",safe=False)
        
        if len(contact_no) != 10:
            return JsonResponse("Contact number must be exactly 10 digits.",safe=False)
        
        errors=[]

        if user.filter(username=username).exists():
            errors.append(f" {username} is already taken , use a different username.")
        
        if  user.filter(contact_no = contact_no).exists():
            errors.append( f" {contact_no} Mobile number already registered, use a different one.")
        
        if user.filter(email=email).exists():
            errors.append(f" {email} already registered  , use a different E-mail.")
        if errors:
            return JsonResponse({"errors":errors},status=400)
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            contact_no = contact_no,
            is_staff=is_staff,
            is_admin = is_admin
        )

        return JsonResponse({"message": f"The user '{user.username}' has successfully registered"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



# @csrf_exempt
# @require_http_methods(["POST"])
# def login_user(request):
#     try:
#         data = json.loads(request.body)
#         username = data.get("username")
#         password = data.get("password")

#         if not username or not password:
#             return JsonResponse({"error": "Username and password are required"}, status=400)

#         user = authenticate(username=username, password=password)
#         if user is None:
#             return JsonResponse({"error": "Invalid credentials"}, status=401)

#         token = generate_jwt(user)

#         return JsonResponse({"token": token, "message": "Login successful"})

#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)











@api_view(["GET"])
@permission_classes([IsAuthenticated])
def movie_list(request):
    title = request.GET.get("title")
    date = request.GET.get("date")
    genre = request.GET.get("genre")
    language = request.GET.get("language")
    

    try:
        #  Parse date if provided
        selected_date = None
        if date:
            try:
                selected_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        
        if selected_date:
            shows = Show.objects.filter(time_slot__date=selected_date)  
            movie_ids = []
            for show in shows:
                if show.movie_id not in movie_ids:
                    movie_ids.append(show.movie_id)

            movies = Movie.objects.filter(id__in=movie_ids)
        else:
            movies = Movie.objects.all()

        #  Apply additional filters
        if genre:
            movies = movies.filter(genres__name__icontains=genre)
        if language:
            movies = movies.filter(language__name__icontains=language)
        if title:
            movies = movies.filter(title__icontains=title)

        if selected_date:
            reference_date = selected_date
        else:
            reference_date = timezone.now().date()


        #  Split into ongoing and upcoming
        ongoing = []
        upcoming = []

        for movie in movies.distinct():
            movie_data = {
                "id": movie.id,
                "title": movie.title,
                "duration_min": movie.duration_min,
            }

            if movie.release_date:
                movie_data["release_date"] = movie.release_date.isoformat()
            else:
                movie_data["release_date"] = None

            if movie.image:
                movie_data["image"] = movie.image.url
            else:
                movie_data["image"] = None

            if movie.release_date and movie.release_date <= reference_date:
                ongoing.append(movie_data)
            else:
                upcoming.append(movie_data)

        return JsonResponse({
            "Now Showing": ongoing,
            "upcoming": upcoming
        })

    except Movie.DoesNotExist:
        return JsonResponse({"error": "Movie not found."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)







@api_view(["GET"])

@permission_classes([IsAuthenticated])
def theater_list (request):
    if request.method == "GET":
        theater_name= request.GET.get("theater_name")
        city = request.GET.get("city")
        location = request.GET.get("location")
        state =request.GET.get("state")
        try:
            theaters = Theater.objects.all()
            #  Apply additional filters
            if theater_name:
                theaters = theaters.filter(name__icontains=theater_name)  
            if city:
                theaters = theaters.filter(city__name__icontains=city)
            if location :
                theaters = theaters.filter(location__icontains=location)
            if state:
                theaters = theaters.filter(city__state__name__icontains=state)
            #listing of theaters
            movie_data=[]
            for theater in theaters :
                theater_list ={
                    " id ": theater.id,
                    " name": theater.name,
                    "city":theater.location,
                    "location":theater.city.name,
                    "state":theater.city.state.name,
                }
                if theaters:
                    movie_data.append(theater_list)
                    
                    
            
            return JsonResponse(movie_data, safe=False)
        except Theater.DoesNotExist:
            return JsonResponse({"error": "Theater does not found."}, status=404)
        except Exception as e:
             return JsonResponse({"error": str(e)}, status=500)



@permission_classes([IsAuthenticated])
@api_view(["GET"])
def booking_info (request):

    try:
      user = request.user
        
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)

    bookings = Bookinginfo.objects.filter(user_id=user)

    booking_info_data=[]
    for booking in bookings:
        seat_numbers = []
        for seat in booking.seats.all():
            seat_numbers.append(seat.seat_number)

        booking_info_data.append({
            "booking_id":booking.id,
            "show_id":booking.show.id,
            "booking_time":booking.booking_time,
            "seat_number":seat_numbers,
            "is_paid":booking.is_paid,

        })
    return JsonResponse({
        "success": True,
        "username": user.username,
        "bookings": booking_info_data
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def explore(request):
    movie_title = request.GET.get("movie_title")
    theater_name = request.GET.get("theater_name")
    location = request.GET.get("location")
    city_name = request.GET.get("city_name")
    date = request.GET.get("date")
    language = request.GET.get("language")
    try:       

        # Validate and parse date
        selected_date = None
        if date:
            try:
                selected_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        shows = Show.objects.all()
        #  filters
        now=timezone.now()

        if selected_date:
            shows = shows.filter(time_slot__gte=now,time_slot__date=selected_date)
        if theater_name:
            shows = shows.filter(theater__name__icontains=theater_name)
        if location:
            shows = shows.filter(theater__location__icontains=location)
        if city_name:
            shows = shows.filter(theater__city__name__icontains=city_name)
        if movie_title:
            shows = shows.filter(movie__title__icontains = movie_title)
        if language:
            shows = shows.filter(language__name__icontains=language)

        result=shows.values('theater').annotate(showtimes=ArrayAgg(JSONObject(id = F('id'), time_slot= F('time_slot'))),                                                                                                                            
                                        movie_id = F('movie__id'),
                                        movie_title=F('movie__title'),
                                        language = F('language__name'),
                                        movie_image =F('movie__image'),
                                        theater_id = F('theater__id'),
                                        theater_name =F('theater__name'),
                                        ).values('movie_id','movie_title','language','movie_image','theater_id','theater_name','showtimes')
        return JsonResponse(list(result),safe=False)
    except Theater.DoesNotExist:
        return JsonResponse({"error": "Theater not found."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    

# @csrf_exempt
# @require_http_methods(["GET"])
# def theater_list_by_movie(request):
#     movie_name = request.GET.get("movie_name")
#     city_name = request.GET.get("city")
#     location = request.GET.get("location")

#     theaters = []
#     seen = set()

#     if not movie_name and not city_name and not location:
#         # No filters at all: return all theaters
#         all_theaters = Theater.objects.select_related('city').all()
#         for theater in all_theaters:
#             if theater.id in seen:
#                 continue
#             seen.add(theater.id)
#             theaters.append({
#                 "theater_id": theater.id,
#                 "theater_name": theater.name,
#                 "location": theater.location,
#                 "city": theater.city.name,
#             })
#         return JsonResponse(theaters, safe=False)

#     # If movie_name is provided, filter shows by movie
#     if movie_name:
#         try:
#             movie = Movie.objects.get(title=movie_name)
#         except Movie.DoesNotExist:
#             return JsonResponse({"error": "Movie not found"}, status=404)

#         shows = Show.objects.filter(movie=movie).select_related('theater', 'theater__city')
#     else:
#         # Get all shows if no movie_name is provided
#         shows = Show.objects.select_related('theater', 'theater__city')

#     for show in shows:
#         theater = show.theater

#         if theater.id in seen:
#             continue

#         # Apply optional city and location filters
#         if city_name and theater.city.name.lower() != city_name.lower():
#             continue
#         if location and location.lower() not in theater.location.lower():
#             continue

#         seen.add(theater.id)
#         theaters.append({
#             "theater_id": theater.id,
#             "theater_name": theater.name,
#             "location": theater.location,
#             "city": theater.city.name,
#             "start_time": show.time_slot if movie_name else None,
#         })

#     return JsonResponse(theaters, safe=False)



LOCK_EXPIRY_MINUTES = 5

@permission_classes([IsAuthenticated])
@api_view(["POST"])
# @transaction.atomic
def initial_booking(request):
    try:
        
        data = json.loads(request.body)
        user = request.user
        show_id = data.get("show_id")
        seat_numbers = data.get("seat_numbers", [])
        # action = data.get("action")  # "lock" or "book"
        # session_id = data.get("session_id")  

        if not user or not show_id or not seat_numbers :
            return JsonResponse({"error": "Missing or invalid fields"}, status=400)
        if len(seat_numbers) > 10:
            return JsonResponse({"error":"can not book seats more than 10."},status=400)
        show = Show.objects.get(id=show_id)
        now = timezone.now()

    
        locked_seats = []
        failed_seats = []
        new_session = None
        try:
            # Check all seats before locking
            with transaction.atomic():
                for seat_num in seat_numbers:
                    try:
                        seat = Seat.objects.get(seat_number=seat_num, theater=show.theater)
                        existing = ShowSeatBooking.objects.filter(show=show, seat=seat).first()

                        if existing:
                            if existing.is_booked:
                                failed_seats.append((seat_num))
                                raise Exception(f"Seat {seat_num} is already booked")
                            session = existing.session_id
                            if (now - session.created_at) < timedelta(minutes=LOCK_EXPIRY_MINUTES):
                                failed_seats.append((seat_num))
                                raise Exception(f"Seat {seat_num} is currently locked")
                                
                            # If seat is already expired then  delete the old session and lock again
                            existing.delete()
                    
                       
                        if not new_session:
                            new_session = Session.objects.create(user=user)

                        ShowSeatBooking.objects.create( show=show,seat=seat,session_id=new_session,is_locked=True )
                        locked_seats.append(seat_num)

                    except Seat.DoesNotExist:
                        failed_seats.append((seat_num, "invalid seat"))

                if locked_seats:
                    return JsonResponse({
                        
                        "payment_url" : f"http://127.0.0.1:8000/payment/?session_id={new_session.session_id}",
                        
                    })
                else:
                    return JsonResponse({"error": "No seats could be locked", "details": failed_seats}, status=400)
                
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    
@csrf_exempt
@require_http_methods(["GET"])
def payment (request):
    session_id =request.GET.get('session_id')
    # user_id = request.GET.get("user_id")
    # show_id = request.GET.get("show_id")
    # seat_numbers =request.GET.get("seat_numbers", [])
    
    if not session_id:
        return JsonResponse({"error": "Session ID is missing"}, status=400)

    return JsonResponse({
        "payment_status": "successful",
        "payment_url" : f"http://127.0.0.1:8000/payment_confirm/?session_id={session_id}",
    })


@permission_classes([IsAuthenticated])
@api_view(["POST","GET"])

def payment_confirm(request):
    try:
        session_id = request.GET.get("session_id")
        if not session_id:
            return JsonResponse({"error": "Session ID is required"}, status=400)

        now = timezone.now()

        try:
            session = Session.objects.get(session_id=session_id)
        except Session.DoesNotExist:
            return JsonResponse({"error": "Invalid session ID"}, status=404)

        if (now - session.created_at) > timedelta(minutes=LOCK_EXPIRY_MINUTES):
            return JsonResponse({"error": "Session expired"}, status=400)


        bookings = ShowSeatBooking.objects.filter(session_id=session, is_locked=True, is_booked=False)

        if not bookings:
            return JsonResponse({"error": "No valid locked seats found for this usser"}, status=400)

        show = bookings.first().show
        user = session.user  
        seat_numbers = []
        for booking in bookings:
            seat_numbers.append(booking.seat.seat_number)

        # Create BookingInfo
        booking_info = Bookinginfo.objects.create(
            user=user,
            theater=show.theater,
            show=show,
            number_of_tickets=bookings.count(),
            is_paid=True
        )

        # Mark seats as booked and link to booking_info
        for booking in bookings:
            booking.is_booked = True
            booking.bookinginfo = booking_info
            booking.save()
            booking_info.seats.add(booking.seat)

        return JsonResponse({
            "message": "Seats successfully booked",
            "booked_seats": seat_numbers,
            "booking_info_id": booking_info.id
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def retrieve_movie(request, movie_id):
    try:
        movie = Movie.objects.get(id=movie_id)
    except Movie.DoesNotExist:
        return JsonResponse({"success": False, "error": "Movie not found"}, status=404)

    image_url = None
    if movie.image:
        image_url = movie.image.url

    languages = []
    for lang in movie.language.all():
        languages.append(lang.name)
    
    genres = []
    for genre in movie.genres.all():
        genres.append(genre.name)

    movie_data = {
        "id": movie.id,
        "title": movie.title,
        "duration_min": movie.duration_min,
        "description": movie.description,
        "release_date": movie.release_date.isoformat(),
        "language": languages,
        "genres": genres,
        "image": image_url,
    }

    return JsonResponse({"success": True, "movie": movie_data}, status=200)






LOCK_EXPIRY_MINUTES = 5


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def show_seat_layout(request):
    show_id = request.GET.get("id")
    try:
        show = Show.objects.get(id=show_id)
    except Show.DoesNotExist:
        return JsonResponse({"success": False, "error": "Show not found"}, status=404)

    now = timezone.now()

    
    bookings = ShowSeatBooking.objects.filter(show=show)

    expired_booking_ids = []
    
    for booking in bookings:
        session = booking.session_id
        if booking.is_locked and session:
            booking_time = session.created_at
            time_differace = now - booking_time
            if time_differace > timedelta(minutes=LOCK_EXPIRY_MINUTES):
                expired_booking_ids.append(booking.id)
            

    if len(expired_booking_ids) > 0:
        ShowSeatBooking.objects.filter(id__in=expired_booking_ids).update(is_locked=False)

    # Re-fetch bookings after cleanup
    bookings = ShowSeatBooking.objects.filter(show=show)

    seat_status = {}

    for booking in bookings:
        seat = booking.seat 
        seat_id = seat.id
 
        if booking.is_booked:
            seat_status[seat_id] = "booked"
        elif booking.is_locked:
            seat_status[seat_id] = "locked"
        else:
            seat_status[seat_id] = "available"
    # print(seat_status)
    
    theater_seats = Seat.objects.filter(theater=show.theater)

    seat_list = []

    for seat in theater_seats:
        seat_list.append({
            "seat_id": seat.id,
            "seat_number": seat.seat_number,
            "status": seat_status.get(seat.id,"available")
        })
        # print(seat_list)


    
    return JsonResponse({
        "success": True,
        "show_id": show.id,
        "seats": seat_list
    })
