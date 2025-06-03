from ticket_booking.models import Seat, Theater

# Choose your theater (use correct ID or filter)
theater = Theater.objects.get(id=12)

# Rows: A to D; Columns: 1 to 10
rows = ['A', 'B', 'C', 'D']
cols = range(1, 11)

seats = []

for row in rows:
    for col in cols:
        seat_number = f"{row}{col}"
        seats.append(Seat(theater=theater, seat_number=seat_number))

# Bulk create all seats at once
Seat.objects.bulk_create(seats)

print(f"{len(seats)} seats created.")

# Command to run  : python manage.py shell < seat_numbering.py
