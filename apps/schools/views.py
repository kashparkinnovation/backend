from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from .models import School, SchoolApprovalStatus
from .serializers import SchoolSerializer, SchoolCreateSerializer, SchoolApprovalSerializer, AdminSchoolCreateSerializer
from apps.users.permissions import IsAdmin, IsVendor, IsAdminOrVendor, IsSchool
from apps.students.models import StudentProfile, VerificationRequest, VerificationStatus
from apps.orders.models import Order, OrderStatus


# ─── Public Views (no authentication required) ─────────────────────────────────

class PublicSchoolListView(generics.ListAPIView):
    """
    GET /api/v1/schools/public/ — List approved schools for the landing / browse page.
    No authentication required.
    """
    serializer_class = SchoolSerializer
    permission_classes = [AllowAny]
    search_fields    = ['name', 'city', 'code']

    def get_queryset(self):
        return (
            School.objects
            .filter(approval_status=SchoolApprovalStatus.APPROVED, is_active=True)
            .select_related('vendor')
            .prefetch_related('coupons')
            .order_by('name')
        )


class PublicSchoolDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/schools/public/<pk>/ — Single approved school detail.
    No authentication required.
    """
    serializer_class = SchoolSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return School.objects.filter(
            approval_status=SchoolApprovalStatus.APPROVED,
            is_active=True,
        ).select_related('vendor')



class SchoolListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/schools/          — Vendor sees own schools; Admin sees all.
    POST /api/v1/schools/          — Vendor applies for a new school (status=pending).
    """
    permission_classes = [IsAdminOrVendor]
    filterset_fields = ['approval_status', 'vendor']
    search_fields = ['name', 'code', 'city']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SchoolCreateSerializer
        return SchoolSerializer

    def get_queryset(self):
        user = self.request.user
        qs = School.objects.select_related('vendor').order_by('-applied_at')
        if user.role == 'vendor':
            return qs.filter(vendor__user=user)
        return qs.all()

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user.vendor_profile)


class SchoolDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/v1/schools/{id}/"""
    permission_classes = [IsAdminOrVendor]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return SchoolCreateSerializer
        return SchoolSerializer

    def get_queryset(self):
        user = self.request.user
        qs = School.objects.select_related('vendor')
        if user.role == 'vendor':
            return qs.filter(vendor__user=user)
        return qs.all()


class SchoolApproveView(generics.UpdateAPIView):
    """
    PATCH /api/v1/schools/{id}/approve/
    Admin approves or rejects a school application.
    """
    serializer_class = SchoolApprovalSerializer
    permission_classes = [IsAdmin]
    queryset = School.objects.all()

    def update(self, request, *args, **kwargs):
        school = self.get_object()
        serializer = self.get_serializer(school, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(SchoolSerializer(updated).data)


class AdminSchoolCreateView(generics.CreateAPIView):
    """
    POST /api/v1/schools/admin-create/
    Admin manually establishes a school and account.
    """
    serializer_class = AdminSchoolCreateSerializer
    permission_classes = [IsAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        school = serializer.save()
        return Response(SchoolSerializer(school).data, status=status.HTTP_201_CREATED)


class SchoolProfileView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/v1/schools/profile/
    School staff user views or updates their own school's profile.
    """
    permission_classes = [IsSchool]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return SchoolCreateSerializer
        return SchoolSerializer

    def get_object(self):
        return get_object_or_404(School, school_user=self.request.user)


class SchoolDashboardView(APIView):
    """
    GET /api/v1/schools/dashboard/
    Stats for the logged-in school user.
    """
    permission_classes = [IsSchool]

    def get(self, request):
        school = getattr(request.user, 'school_profile', None)
        if not school:
            return Response({'detail': 'No school profile found'}, status=403)

        total_students = StudentProfile.objects.filter(school=school).count()
        verified_students = StudentProfile.objects.filter(school=school, is_verified=True).count()
        pending_verifications = VerificationRequest.objects.filter(
            student__school=school, status=VerificationStatus.PENDING
        ).count()

        total_orders = Order.objects.filter(school=school).count()
        active_orders = Order.objects.filter(
            school=school
        ).exclude(status__in=[OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.REFUNDED]).count()
        
        delivered_count = Order.objects.filter(
            school=school, status=OrderStatus.DELIVERED
        ).count()

        return Response({
            'total_students': total_students,
            'verified_students': verified_students,
            'pending_verifications': pending_verifications,
            'total_orders': total_orders,
            'active_orders': active_orders,
            'delivered_count': delivered_count,
            'school_name': school.name,
        })


from .models import VendorChangeRequest, VendorChangeRequestStatus
from .serializers import VendorChangeRequestSerializer
from apps.vendors.models import Vendor

class AdminRequestVendorChangeView(generics.CreateAPIView):
    """
    POST /api/v1/schools/<id>/request-vendor-change/
    Admin applies to change a school's vendor.
    """
    serializer_class = VendorChangeRequestSerializer
    permission_classes = [IsAdmin]

    def create(self, request, pk=None):
        school = get_object_or_404(School, pk=pk)
        new_vendor_id = request.data.get('new_vendor')
        if not new_vendor_id:
            return Response({'detail': 'New vendor ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        new_vendor = get_object_or_404(Vendor, id=new_vendor_id)
        
        # Prevent creating if there's already a pending request for this school
        if VendorChangeRequest.objects.filter(school=school, status=VendorChangeRequestStatus.PENDING).exists():
            return Response({'detail': 'A vendor change request is already pending for this school.'}, status=status.HTTP_400_BAD_REQUEST)

        change_request = VendorChangeRequest.objects.create(
            school=school,
            old_vendor=school.vendor,
            new_vendor=new_vendor,
            status=VendorChangeRequestStatus.PENDING
        )
        return Response(VendorChangeRequestSerializer(change_request).data, status=status.HTTP_201_CREATED)


class SchoolVendorChangeRequestView(generics.ListAPIView):
    """
    GET /api/v1/schools/vendor-change-requests/
    School staff lists change requests targeting their institution.
    """
    serializer_class = VendorChangeRequestSerializer
    permission_classes = [IsSchool]

    def get_queryset(self):
        school = getattr(self.request.user, 'school_profile', None)
        if not school:
            return VendorChangeRequest.objects.none()
        return VendorChangeRequest.objects.filter(school=school)


class SchoolVendorChangeApprovalView(generics.UpdateAPIView):
    """
    PATCH /api/v1/schools/vendor-change-requests/<id>/approve/
    School staff user approves or rejects administrative reassignment.
    """
    serializer_class = VendorChangeRequestSerializer
    permission_classes = [IsSchool]

    def get_queryset(self):
        school = getattr(self.request.user, 'school_profile', None)
        if not school:
            return VendorChangeRequest.objects.none()
        return VendorChangeRequest.objects.filter(school=school, status=VendorChangeRequestStatus.PENDING)

    def update(self, request, *args, **kwargs):
        change_request = self.get_object()
        action = request.data.get('action') # 'approve' or 'reject'
        
        if action == 'approve':
            change_request.status = VendorChangeRequestStatus.APPROVED
            change_request.save()
            
            # Apply vendor shift to actual school parameters securely!
            school = change_request.school
            school.vendor = change_request.new_vendor
            school.save()
            
            return Response({'detail': 'Vendor changed successfully', 'request': VendorChangeRequestSerializer(change_request).data})
        elif action == 'reject':
            change_request.status = VendorChangeRequestStatus.REJECTED
            change_request.save()
            return Response({'detail': 'Vendor reassignment rejected', 'request': VendorChangeRequestSerializer(change_request).data})
        else:
            return Response({'detail': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
