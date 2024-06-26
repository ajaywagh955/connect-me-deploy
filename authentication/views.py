from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from datetime import datetime,timedelta
from django.urls import reverse
from authentication.models import UserProfile
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db import IntegrityError
import uuid
import random
import re
# Create your views here.

def UserLogin(request):       
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user_entered_otp = request.POST.get("otp")
        
        if user_entered_otp is None:

            user_obj = User.objects.filter(username=email).first()
            
            if user_obj is None:
                messages.success(request, "User Not Found")
                return render(request, "authentication/login.html",{"email":email})
            
            user = authenticate(username=email, password=password)
            
            profile_obj = UserProfile.objects.filter(user=user_obj).first()

            if not profile_obj.is_varified:
                messages.success(request, "Your account is not varified please check your email")
                return render(request, "authentication/login.html",{"email":email}) 
            
            if user is None:
                messages.success(request, "Wrong Password")
                return render(request, "authentication/login.html",{"email":email})           
  
            
            generated_otp = random.randint(11111,99999)           
            auth_user = User.objects.filter(username=email).first()            
            user_name = auth_user.first_name            
            otp_save = UserProfile.objects.get(user=auth_user)
            otp_save.otp = generated_otp
            otp_save.otp_expiration_time = timezone.now() + timedelta(minutes=5)
            otp_save.save()
            
            send_mail_after_login(email,generated_otp,user_name)
            
            next_url = request.GET.get('next')
            
            if next_url:
                return redirect(next_url)
            else:
                return render(request, "authentication/login.html",{"email":email,"otp_text":"Please varify Your OTP sent on Your Registered Email"})
            
        else:
            auth_user = User.objects.filter(username=email).first()
            
            otp_save_database = UserProfile.objects.get(user=auth_user)
            current_time = timezone.now()
            
            if otp_save_database.otp_expiration_time < current_time:
                return render(request, "authentication/login.html", {"email": email, "otp_text": "OTP has been expired"})              
            
            already_saved_otp = otp_save_database.otp
            
            if already_saved_otp == user_entered_otp:
                random_otp = random.randint(1000000,9999999999)
                
                otp_save_database.otp = random_otp
                otp_save_database.save()
                
                login(request, auth_user)
                return redirect("/")
            else:
                return render(request, "authentication/login.html", {"email": email, "otp_text": "Invalid OTP"})
            
    
    return render(request, "authentication/login.html")


def send_mail_after_login(email, generated_otp,user_name):
    subject = 'OTP Verification'
    html_content = render_to_string('authentication/send_otp.html', {'user_name': user_name, 'generated_otp': generated_otp})
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def UserRegister(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        
        generate_username = email.split('@')[0]
        generate_username = re.sub(r'\W+','',generate_username)

        if User.objects.filter(username=email).exists():
            messages.success(request, "Email already taken")
            return render(request, 'authentication/register.html', {"name": name, "email": email})
        
        # Create the User instance
        user = User.objects.create_user(username=email, password=password, email=email, first_name=name, last_name=generate_username)
        
        # Create the UserProfile associated with the user
        auth_token = str(uuid.uuid4())
        user_profile = UserProfile.objects.create(user=user, auth_token=auth_token, username=generate_username)
        
        # Save the UserProfile
        user_profile.save()
        
        # Send registration confirmation email
        send_mail_after_registration(email, auth_token, name)
                
        return redirect("token_send")
        
    return render(request, 'authentication/register.html')


def token_send(request):
    return render(request,'authentication/token_send.html')


def RegistrationVarify(request,auth_token):
    try:
        profile_obj = UserProfile.objects.filter(auth_token=auth_token).first()


        if profile_obj:
            if profile_obj.is_varified:
                messages.success(request, "Your account is already varified")
                return redirect('login')
            
            profile_obj.is_varified = True
            profile_obj.save()
            messages.success(request, "Your account has been varified")
            
            return redirect('login')
        else:
            return redirect('/error')
    except Exception as e:
        print(e)
        
        
def Suceess(request):
    return render(request,'authentication/success.html')


def send_mail_after_registration(email, token, name):
    subject = 'Email Confirmation || ConnectME'
    html_content = render_to_string('authentication/email_confirmation.html', {'name': name, 'token': token})
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()

     
@login_required(login_url="login")  
def UpdateProfile(request):
        if request.method == "POST":
            first_name = request.POST.get("full_name")
            mobile_number = request.POST.get("mobile_number")
            gender = request.POST.get("gender")
            user_bio = request.POST.get("user_bio")
            username = request.POST.get("username")
            email = request.POST.get("email")
            
            user_profile = UserProfile.objects.filter(user=request.user).first()
            
            user_profile.user.first_name = first_name
            user_profile.mobile_number = mobile_number
            user_profile.gender = gender
            user_profile.user_bio = user_bio
            
            user_profile.save()   
            
            # Handle profile picture upload
            if 'profile_image' in request.FILES:
                profile_picture = request.FILES['profile_image']
                user_profile.profile_picture = profile_picture
            
            # Handle cover image upload
            if 'cover_image' in request.FILES:
                cover_image = request.FILES['cover_image']
                user_profile.cover_picture = cover_image
                
            # Save the updated profile
            user_profile.save()          
            
            return redirect(reverse('profile', args=[username]))
        
        return HttpResponse("Update Profile Form Endpoint")
        