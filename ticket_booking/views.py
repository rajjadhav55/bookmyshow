import os
import random
import json , uuid
from weasyprint import HTML
from datetime import datetime
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.shortcuts import  render
from django.db.models import Min , F
from django.core.mail import send_mail
from email.message import  EmailMessage
from django.utils.html import format_html
from django.core.mail import  EmailMessage
from rest_framework.response import Response
from django.templatetags.static import static
from django.contrib.auth import get_user_model
from django.db.models.functions import JSONObject
from django.http import JsonResponse ,HttpResponse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from .models import Theater , Movie , Show , Bookinginfo , Genre , Language ,Seat ,ShowSeatBooking, customUser, Session , OTPStorage , City


User = get_user_model() 
LOCK_EXPIRY_MINUTES = 5
OTP_RESEND_MINUTES = 1
BLOCK_USER_MINUTES = 10
OTP_LIFE_SPAN = 1
now = timezone.now()



@csrf_exempt
def send_otp(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Only POST method allowed'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)

    if not email:
        return JsonResponse({'success': False, 'message': 'Email is required'}, status=400)

    now = timezone.now()

    try:
        last_otp = OTPStorage.objects.filter(email=email).latest()
        time_diff = now - last_otp.created_at

        # If too soon to resend
        if time_diff < timedelta(minutes=OTP_RESEND_MINUTES):
            return JsonResponse({'success': False, 'message': 'Please wait 60 seconds before requesting another OTP'}, status=400)

        # Reset counter after BLOCK_USER_MINUTES
        if time_diff > timedelta(minutes=BLOCK_USER_MINUTES):
            previous_counter = 0
        else:
            previous_counter = last_otp.counter

        # Block if too many attempts
        if previous_counter >= 3:
            return JsonResponse({'success': False, 'message': 'Too many attempts. Try again in sometime.'}, status=400)

    except OTPStorage.DoesNotExist:
        previous_counter = 0

    # Expire all valid old OTPs before sending a new one
    OTPStorage.objects.filter(email=email,is_expired=False).update(is_expired=True)

    # Generate new OTP
    otp = str(random.randint(100000, 999999))
    OTPStorage.objects.create(
        email=email,
        otp=otp,
        counter=previous_counter + 1,
        is_expired=False
    )

    # Email message
    subject = "Your OTP Code"
    body = format_html(f'''
    <div style="
        font-family: 'Helvetica Neue', Arial, sans-serif; 
        color: #333; 
        text-align: center; 
        border: 2px solid #0057ff; 
        padding: 25px; 
        margin: 20px auto; 
        border-radius: 12px; 
        max-width: 600px; 
        box-shadow: 0px 4px 12px rgba(0,0,0,0.2);
    ">
        <p style="font-size: 20px; font-weight: bold; color: #0057ff;">🔒 Secure Verification</p>
        <p style="font-size: 16px;">Dear User,</p>
        <p style="font-size: 16px;">Your One-Time Password (OTP) for verification is:</p>
        <div style="
            background-color: #0057ff;
            color: white;
            font-size: 32px;
            padding: 18px 30px;
            display: inline-block;
            border-radius: 10px;
            margin: 15px 0;
            font-weight: bold;
            letter-spacing: 4px;
            text-align: center;
            box-shadow: 0px 5px 10px rgba(0,0,0,0.3);
        ">{otp}</div>
        <p style="font-size: 16px; font-weight: bold; color: #d32f2f;">⚠️ This OTP is valid for 5 minutes. Do not share it with anyone.</p>
        <p style="font-size: 14px; color: #555;">If you did not request this, please ignore this email.</p>
        <div style="border-top: 2px solid #0057ff; margin: 20px auto; width: 60%;"></div>
        <p style="font-size: 16px;">Best regards,</p>
        <p style="font-size: 18px; font-weight: bold; color: #0057ff;">Team BookMyShow</p>
    </div>
''')








    email_message = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.EMAIL_HOST_USER,
        to=[email],
    )
    email_message.content_subtype = 'html'
    email_message.send(fail_silently=False)

    return JsonResponse({'success': True, 'message': 'OTP sent successfully'})




@csrf_exempt
def verify_otp(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        otp = data.get('otp')
    except (json.JSONDecodeError, KeyError, TypeError):
        return JsonResponse({'success': False, 'message': 'Invalid request data'}, status=400)

    if not email or not otp:
        return JsonResponse({'success': False, 'message': 'Email and OTP are required'}, status=400)

    now = timezone.now()

    try:
        otp_entry = OTPStorage.objects.get(email=email, otp=otp)
    except OTPStorage.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid OTP'}, status=400)

    
    if (now - otp_entry.created_at) > timedelta(minutes=LOCK_EXPIRY_MINUTES):
        otp_entry.is_expired = True
        otp_entry.save()
        return JsonResponse({'success': False, 'message': 'OTP expired'}, status=400)

    
    if otp_entry.is_expired:
        return JsonResponse({'success': False, 'message': 'OTP already expired'}, status=400)

    
    otp_entry.is_expired = True
    otp_entry.save()

    return JsonResponse({'success': True, 'message': 'OTP verified successfully'}, status=200)



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
def language_list(request):
    languages = request.GET.get("language")

    language = Language.objects.all()
    try:
        if languages:
            language = language.filter(name__icontains=languages)

        lang=[]
        for languages in language:
            lang.append(languages.name)

        return JsonResponse({
                "languages":lang
            })
    except Language.DoesNotExist:
        return JsonResponse({"error": "language not found."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def genre_list (request):
    genres = request.GET.get('genre')

    genre = Genre.objects.all()
    try:
        if genres:
            genre = genre.filter(name__icontains=genres)

        genre_list=[]
        for genres in genre:
            genre_list.append(genres.name)

        return JsonResponse({
                "genres":genre_list
            })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)





@api_view(["GET"])
@permission_classes([IsAuthenticated])
def city_list (request):
    city=request.GET.get('city')
    citys = City.objects.all()
    if city :
        citys = citys.filter(name__icontains=city)
    try:
        city_list=[]
        for city in citys:
            city_list.append(city.name)
            
        return JsonResponse({
                "citys":city_list
            })
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
      if not user.is_authenticated:
          return JsonResponse({"success": False, "error": "User not authenticated"}, status=401)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)

    bookings = Bookinginfo.objects.filter(user_id=user)

    booking_info_data=[]
    for booking in bookings:
        seat_numbers = []
        for seat in booking.seats.all():
            seat_numbers.append(seat.seat_number)
            movie = booking.show.movie
            if movie.image:
                movie_image_url = movie.image.url
            else:
                movie_image_url = None

        booking_info_data.append({
            "booking_id":booking.id,
            "movie_title": booking.show.movie.title,
            "movie_image": movie_image_url,
            "theater_name": booking.show.theater.name,
            "show_id":booking.show.id,
            "show_date": booking.show.time_slot.date(),
            "showtime": booking.show.time_slot.strftime("%I:%M %p"),
            "booking_date":booking.booking_time.date(),
            "booking_time":booking.booking_time.strftime("%I:%M %p"),
            "seat_number":seat_numbers,
            "total_price": f'₹{booking.show.price * booking.number_of_tickets}/-',
            "is_paid":booking.is_paid,
                    
                    
                })
        
    return JsonResponse({
        "success": True,
        "username": user.username,
        "bookings": booking_info_data
    })










@login_required
def generate_invoice_pdf(request, booking_id):
    booking = Bookinginfo.objects.get(id=booking_id, user=request.user)
    seat_numbers = []
    for seat in booking.seats.all():
        seat_numbers.append(seat.seat_number)

    
    image_url = request.build_absolute_uri(booking.show.movie.image.url)

   
    html_string = render_to_string('ticket.html', {
        'booking': booking,
        'seat_numbers': seat_numbers,
        'image_url': image_url,
        "total_price": f'₹{booking.show.price * booking.number_of_tickets}/-',
    })

    # Generate PDF with base URL to load external assets
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

    # Return the PDF as a downloadable response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=Invoice_{booking.id}.pdf'
    return response



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def explore(request):
    movie_title = request.GET.get("movie_title")
    theater_name = request.GET.get("theater_name")
    location = request.GET.get("location")
    city_name = request.GET.get("city_name")
    date = request.GET.get("date")
    language = request.GET.get("language")
    price1= request.GET.get("price1")
    price2= request.GET.get("price2")
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
            shows = shows.filter(language__name__icontains = language)
        if price1 and price2:
              
            try:
                shows = shows.filter(price__range=(price1, price2))
            except ValueError:
                return JsonResponse({"error": "Price values must be valid numbers."}, status=400)
        
        result=shows.values('theater').annotate(showtimes=ArrayAgg(JSONObject(id = F('id'),
                                                                              time_slot= F('time_slot'),
                                                                              language = F('language__name'),                                                                                                                            
                                                                              price= F('price'))),
                                        movie_id = F('movie__id'),
                                        theater_id = F('theater__id'),
                                        movie_title=F('movie__title' ),                                  
                                        movie_image =F('movie__image' ),
                                        theater_name =F('theater__name'),
                                        theater_location = F('theater__location')
                                        

                                        ).values('movie_id','movie_title','movie_image','theater_id','theater_name','theater_location','showtimes')
        
        return JsonResponse(list(result),safe=False)
    except Theater.DoesNotExist:
        return JsonResponse({"error": "Theater not found."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    


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

        show_time=show.time_slot
        if now > show_time:
            return JsonResponse({"error": "show is unavailabe"}, status=400)
        
    
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
@api_view(["POST", "GET"])
def payment_confirm(request):
    try:
        with transaction.atomic():
            session_id = request.GET.get("session_id")
            if not session_id:
                return JsonResponse({"error": "Session ID is required"}, status=400)

            now = timezone.now()

            try:
                session = Session.objects.get(session_id=session_id)
            except Session.DoesNotExist:
                raise Exception("Invalid session ID")

            if (now - session.created_at) > timedelta(minutes=LOCK_EXPIRY_MINUTES):
                raise Exception("locking - Session expired")

            bookings = ShowSeatBooking.objects.filter(
                session_id=session, is_locked=True, is_booked=False
            )

            if not bookings.exists():
                return JsonResponse({"error": "No valid locked seats found for this user"}, status=400)

            show = bookings.first().show
            user = session.user

            # Create BookingInfo
            booking_info = Bookinginfo.objects.create(
                user=user,
                theater=show.theater,
                show=show,
                number_of_tickets=bookings.count(),
                is_paid=True
            )

            # Mark seats as booked and link to booking_info
            seat_numbers = []
            for booking in bookings:
                booking.is_booked = True
                booking.bookinginfo = booking_info
                booking.save()
                booking_info.seats.add(booking.seat)
                seat_numbers.append(booking.seat.seat_number)

            # Get image URLs
            image_url = request.build_absolute_uri(booking.show.movie.image.url)
            stamp_url = request.build_absolute_uri('/media/confirmed-vector-stamp-isolated-on-600nw-1561368712.webp')

            # Render email content
            html_content = render_to_string('email_ticket.html', {
                'booking': booking_info,
                'seat_numbers': seat_numbers,
                'movie_image_url': image_url,
                'stamp_image_url': stamp_url,
                'total_price': show.price * bookings.count(),
            })

            text_content = f"Your booking for {show.movie.title} has been confirmed. Seats: {', '.join(seat_numbers)}."

            # Send email
            email = EmailMultiAlternatives(
                subject=f"🎬 Booking Confirmed: {show.movie.title}",
                body=text_content,
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            return JsonResponse({
                "message": "Seats successfully booked",
                "user_email": user.email,
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
#--------------------------------------------my_bookings-----------------------------------------------------#
# @login_required
# def my_bookings(request):
#     user = request.user

#     # Get all bookings for the user
#     bookings = Bookinginfo.objects.filter(user=user)

#     booking_info_data = []

#     for booking in bookings:
#         # Get seat numbers as a list
#         seat_numbers = []
#         for seat in booking.seats.all():
#             seat_numbers.append(seat.seat_number)

#         # Get movie image URL or None
#         movie = booking.show.movie
#         if movie.image:
#             movie_image_url = movie.image.url
#         else:
#             movie_image_url = None

        
        

#         # Prepare row data
#         booking_info_data.append({
#             "id": booking.id,
#             "show_date": booking.show.time_slot.date(),
#             "movie_title": movie.title,
#             "movie_image": movie_image_url,
#             "showtime": booking.show.time_slot.strftime("%I:%M %p"),
#             "seat_number": seat_numbers,
#             "theater_name": booking.show.theater.name,
#             "booking_time": booking.booking_time,
#             "total_price": booking.show.price * booking.number_of_tickets,
#             "is_paid": booking.is_paid

#         })

#     return render(request, 'ticket.html', {
#         'data': booking_info_data
#     })

#--------------------------------------theater_list_by_movie-------------------------------------------------#

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


#------------------------------------------------login_user--------------------------------------------------#


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

#------------------------------------------------------------------------------------------------------------#