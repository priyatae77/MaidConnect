from maidapp.models import CustomUser, WorkerProfile, Booking, Payment

u, _ = CustomUser.objects.get_or_create(username='test_payer', defaults={'role': 'user'})
u.set_password('password123')
u.save()

w_u, _ = CustomUser.objects.get_or_create(username='worker_bob', defaults={'role': 'worker'})
w, _ = WorkerProfile.objects.get_or_create(user=w_u, defaults={'address': 'Test', 'location': 'Test', 'skills': 'Cleaning', 'experience': 5, 'price_per_day': 600})

b, _ = Booking.objects.get_or_create(user=u, worker=w)
b.status = 'confirmed'
b.save()
