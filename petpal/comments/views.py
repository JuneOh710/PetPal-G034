# from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from django.core.paginator import Paginator
from django.http import JsonResponse
from applications.models import Application
from .models import Comment
from accounts.models import PetPalUser as User

'''
CREATE New Comment
ENDPOINT: /api/comments
METHOD: POST
PERMISSION: User logged in and must be part of the application if is_review == False
SUCCESS:
'''
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comment_create_view(request):
    is_author_seeker = True if request.user.role == User.Role.SEEKER else False
    is_review = request.data.get('is_review')
    content = request.data.get('content')
    if content.strip() == '':
        return Response({'error': 'Content cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)

    if request.data.get('recipient_email') == None or request.data.get('recipient_email').strip() == '':
        return Response({'error': 'Recipient email cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if email is seeker -> shelter, shelter -> seeker
    if request.user.role == User.objects.get(email=request.data.get('recipient_email')).role:
        return Response({'error': f'{request.user.role}-{request.user.role} communication not supported'}, status=status.HTTP_400_BAD_REQUEST)
    
    if is_author_seeker:
        seeker_email = request.user.email
        shelter_email = request.data.get('recipient_email')
    else:
        shelter_email = request.user.email
        seeker_email = request.data.get('recipient_email')
    
    if is_review == None or is_author_seeker == None or content == None or seeker_email == None or shelter_email == None:
        return Response({'error': 'Missing fields'}, status=status.HTTP_400_BAD_REQUEST)
    
    if is_review == False:
        # Application message
        application_id = request.data.get('application_id')
        try:
            application = Application.objects.get(pk=application_id)
            # Check if user is part of the application
            if request.user != application.seeker and request.user != application.petlisting.owner:
                return Response({'error': 'User not authorized to comment on this application'}, status=status.HTTP_401_UNAUTHORIZED)
            new_comment = Comment(content=content, is_author_seeker=is_author_seeker, seeker=application.seeker, shelter=application.petlisting.owner, is_review=is_review, application=application)
            new_comment.save()
            return JsonResponse({'msg': 'Comment Created'}, status=status.HTTP_200_OK)
        except Exception as e: 
            # might also fail at save(), not necessarily "comment doesn't exist"
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    else:
        # Shelter comment
        try:
            seeker = User.objects.get(email=seeker_email)
            shelter = User.objects.get(email=shelter_email)
            rating = request.data.get('rating')
            new_comment = Comment(content=content, is_author_seeker=is_author_seeker, seeker=seeker, shelter=shelter, is_review=is_review, rating=rating)
            new_comment.save()
            return Response({'msg': 'Review Created'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

'''
VIEW A Comment
ENDPOINT: /api/comments/<int:msg_id>
METHOD: GET
PERMISSION: User logged in and must be the author or recipient of the comment
'''
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def comment_detail_view(request, msg_id):
    try:
        comment = Comment.objects.get(pk=msg_id)
        if request.user != comment.seeker and request.user != comment.shelter:
            return Response({'error': 'User not authorized to view this comment'}, status=status.HTTP_401_UNAUTHORIZED)
        data = {
            "id": comment.pk,
            "content": comment.content,
            "created_time": comment.created_time,
            "rating": comment.rating,
            "is_author_seeker": comment.is_author_seeker,
            "seeker": comment.seeker.email,
            "shelter": comment.shelter.email,
            "is_review": comment.is_review,
            "application": comment.application.pk,
        }
        return Response({'data': data}, status=status.HTTP_200_OK)
    except:
        return Response({'error': 'Comment does not exist'}, status=status.HTTP_400_BAD_REQUEST)

'''
LIST All Comments of a User's All Applications
ENDPOINT: /api/comments/applications
METHOD: GET
PERMISSION: User logged in
FE: Message Center
Returns in form:
{application_id: [comments], application_id: [comments], ...}
'''
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def comments_all_applications_list_view(request):
    try:
        if request.user.role == 'SHELTER':
            user_applications = User.objects.get(pk=request.user.pk).shelter_applications.all()
        else:
            user_applications = User.objects.get(pk=request.user.pk).seeker_applications.all()
        data = {}

        # Visualization: Message center with a message preview so paginating user_applications not comments
        paginator = Paginator(user_applications, per_page=1)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        
        for application in page_obj.object_list:
            
            data[application.pk] = []
            comments = application.comment_set.all().order_by('-created_time')
        
            # for comment in comments[:2]: # fixed length preview pagination, use for P3
            for comment in comments:
                data[application.pk].append({
                    "id": comment.pk,
                    "content": comment.content,
                    "created_time": comment.created_time,
                    "rating": comment.rating,
                    "is_author_seeker": comment.is_author_seeker,
                    "seeker": comment.seeker.email,
                    "shelter": comment.shelter.email,
                    "is_review": comment.is_review,
                    "application": comment.application.pk,
                })

        payload = {
            "page": {
                "current": page_obj.number,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
            "data": data
        }
        
        return Response(payload, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

'''
LIST All Comments of a Certain Application
ENDPOINT: /api/comments/applications/<int:app_id>
METHOD: GET
PERMISSION: User logged in and must be part of the application
FE: Message History with Shelter, Convo Name: Application
'''
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def comments_application_list_view(request, app_id):
    try:
        application = Application.objects.get(pk=app_id)
        if request.user != application.seeker and request.user != application.shelter:
            return Response({'error': 'User not authorized to view this comment list'}, status=status.HTTP_401_UNAUTHORIZED)

        data = []
        comments = application.comment_set.all().order_by('-created_time')

        # pagination
        paginator = Paginator(comments, per_page=2)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        for comment in page_obj.object_list:
            data.append({
                "id": comment.pk,
                "content": comment.content,
                "created_time": comment.created_time,
                "rating": comment.rating,
                "is_author_seeker": comment.is_author_seeker,
                "seeker": comment.seeker.email,
                "shelter": comment.shelter.email,
                "is_review": comment.is_review,
                "application": comment.application.pk,
            })

        payload = {
            "page": {
                "current": page_obj.number,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
            "data": data
        }
        
        return Response(payload, status=status.HTTP_200_OK)
    except:
        return Response({'error': 'Application does not exist'}, status=status.HTTP_400_BAD_REQUEST)

'''
LIST All Comments of a Shelter
ENDPOINT: /api/comments/shelter/<int:shelter_id>
METHOD: GET
PERMISSION: User logged in
'''
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def comments_shelter_list_view(request, shelter_id):
    try:
        shelter = User.objects.get(pk=shelter_id)
        if shelter.role != 'SHELTER':
            return JsonResponse({'data': 'Shelter does not exist'}, status=status.HTTP_400_BAD_REQUEST)
        
        comments = Comment.objects.filter(shelter=shelter, is_review=True).order_by('-created_time')
        data = []

        # pagination
        paginator = Paginator(comments, per_page=1)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # for comment in page_obj.object_list:
        for comment in page_obj:
            data.append({
                "id": comment.pk,
                "content": comment.content,
                "created_time": comment.created_time,
                "rating": comment.rating,
                "is_author_seeker": comment.is_author_seeker,
                "seeker": comment.seeker.email,
                "shelter": comment.shelter.email,
                "is_review": comment.is_review,
                "application": comment.application,
            })

        payload = {
            "page": {
                "current": page_obj.number,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
            "data": data
        }

        return JsonResponse(payload, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)