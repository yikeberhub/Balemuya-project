from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import ServicePost, ServicePostApplication, ServiceBooking
from common.models import Category
from .serializers import ServicePostSerializer
from users.models import Professional, Customer

from django.http import JsonResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class ServicePostAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        if pk:
            try:
                service_post = ServicePost.objects.get(id=pk)
                serializer = ServicePostSerializer(service_post)
                return Response(serializer.data)
            except ServicePost.DoesNotExist:
                return Response({"detail": "ServicePost not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            service_posts = ServicePost.objects.all()
            if not service_posts:
                return Response({"detail": "No service posts found."}, status=status.HTTP_404_NOT_FOUND)
            serializer = ServicePostSerializer(service_posts, many=True)
            return Response(serializer.data)

    def post(self, request):
        if request.user.user_type != "customer":
            return Response({"detail": "Only customers can create service posts."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ServicePostSerializer(data=request.data)
        if serializer.is_valid():
            service_post = serializer.save(customer=request.user.customer)
            
            
            # # Notify professionals in the same category
            # category_name = service_post.category.name  # Assuming 'category' has a 'name' field
            # async_to_sync(channel_layer.group_send)(
            #     f"category_{category_name}",
            #     {
            #         "type": "send_notification",
            #         "data": {
            #             "title": "New Service Posted",
            #             "description": service_post.description,
            #             "urgency": service_post.urgency,
            #             "due_date": service_post.work_due_date.isoformat() if service_post.work_due_date else None,
            #             "customer": service_post.customer.user.username,
            #         },
            #     },
            # )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk=None):
        try:
            service_post = ServicePost.objects.get(id=pk, customer=request.user.customer)
        except ServicePost.DoesNotExist:
            return Response({"detail": "ServicePost not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ServicePostSerializer(service_post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        try:
            service_post = ServicePost.objects.get(id=pk)
        except ServicePost.DoesNotExist:
            return Response({"detail": "ServicePost not found."}, status=status.HTTP_404_NOT_FOUND)

        service_post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ServicePostApplicationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_post_id=None, pk=None):
        if pk:
            try:
                application = ServicePostApplication.objects.get(id=pk)
                serializer = ServicePostApplicationSerializer(application)
                return Response(serializer.data)
            except ServicePostApplication.DoesNotExist:
                return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            applications = ServicePostApplication.objects.filter(service_id=service_post_id)
            serializer = ServicePostApplicationSerializer(applications, many=True)
            return Response(serializer.data)

    def post(self, request, service_post_id=None):
        serializer = ServicePostApplicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(service_id=service_post_id, customer=request.user.customer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk=None):
        try:
            application = ServicePostApplication.objects.get(id=pk)
        except ServicePostApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ServicePostApplicationSerializer(application, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        try:
            application = ServicePostApplication.objects.get(id=pk)
        except ServicePostApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)
        
        application.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    

class ServiceBookingAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            try:
                booking = ServiceBooking.objects.get(id=pk)
                serializer = ServiceBookingSerializer(booking)
                return Response(serializer.data)
            except ServiceBooking.DoesNotExist:
                return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            bookings = ServiceBooking.objects.all()
            serializer = ServiceBookingSerializer(bookings, many=True)
            return Response(serializer.data)

    def post(self, request):
        application_id = request.data.get('service_post_application')
        try:
            application = ServicePostApplication.objects.get(id=application_id)
        except ServicePostApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if application.status != 'accepted':
            return Response({"detail": "Only accepted applications can be booked."}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ServiceBookingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(service_post_application=application, professional=application.professional)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk=None):
        try:
            booking = ServiceBooking.objects.get(id=pk)
        except ServiceBooking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ServiceBookingSerializer(booking, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        try:
            booking = ServiceBooking.objects.get(id=pk)
        except ServiceBooking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
        
        booking.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
