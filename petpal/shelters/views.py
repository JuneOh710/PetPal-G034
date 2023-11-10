# from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from accounts.models import PetPalUser, Shelter
from .serializers import ShelterSerializer
from django.core.paginator import Paginator

from django.http import JsonResponse

# Create your views here.

'''
LIST All Shelters
ENDPOINT: /api/shelters
METHOD: GET
PERMISSION:
'''


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shelters_list_view(request):
    shelters = Shelter.shelter.all()
    # serializer = ShelterSerializer(shelters, many=True)
    data = []

    # -- Pagination --
    # Picks how many shelters to show per page
    paginator = Paginator(shelters, per_page=3)
    # Retrieve page number
    page_num = request.GET.get("page", 1)
    # Get shelters from that page number
    page_obj = paginator.get_page(page_num)

    # Append each shelter of the page in data lst
    for shelter in page_obj.object_list:
        data.append({
            'id': shelter.pk,
            'email': shelter.email,
            'address': shelter.address,
            'city': shelter.city,
            'province': shelter.province,
            'postal_code': shelter.postal_code,
            'phone': shelter.phone,
            'avatar': shelter.avatar,
            'description': shelter.description
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


'''
VIEW / EDIT / DELETE A shelter
ENDPOINT: /api/shelters/<int:account_id>/
METHOD: GET, PUT, DELETE
PERMISSION:
SUCCESS:
'''


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def shelter_detail_view(request, account_id):
    # Check that the shelter exists
    try:
        shelter = Shelter.objects.get(id=account_id)
    except Shelter.DoesNotExist:
        return Response({'error': 'Shelter does not exist'}, status=status.HTTP_404_NOT_FOUND)

    # METHODS
    if request.method == 'GET':
        # Give details of the shelter
        serializer = ShelterSerializer(shelter, many=False)
        return Response({'msg': 'Shelter Detail', 'data': serializer.data}, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        # Check that the request is from the shelter themselves
        if request.user == shelter:
            shelter.email = request.data.get('email', shelter.email)
            shelter.address = request.data.get('address', shelter.address)
            shelter.city = request.data.get('city', shelter.city)
            shelter.province = request.data.get('province', shelter.province)
            shelter.postal_code = request.data.get('postal_code', shelter.postal_code)
            shelter.phone = request.data.get('phone', shelter.phone)
            shelter.avatar = request.data.get('avatar', shelter.avatar)
            shelter.description = request.data.get('description', shelter.description)
            shelter.password = request.data.get('password', shelter.password)  # not sure if we should have password?

            serialized = ShelterSerializer(shelter, many=False)

            return Response({'msg': 'edit shelter', 'data': serialized.data}, status=status.HTTP_200_OK)

        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
