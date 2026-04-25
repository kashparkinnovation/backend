from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from .models import School, SchoolApprovalStatus
from .serializers import SchoolSerializer, SchoolCreateSerializer, SchoolApprovalSerializer
from apps.users.permissions import IsAdmin, IsVendor, IsAdminOrVendor, IsSchool
from apps.students.models import StudentProfile, VerificationRequest, VerificationStatus
from apps.orders.models import Order, OrderStatus, DistributionStatus


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
        
        ready_for_pickup = Order.objects.filter(
            school=school,
            distribution_status=DistributionStatus.READY_FOR_PICKUP
        ).count()

        return Response({
            'total_students': total_students,
            'verified_students': verified_students,
            'pending_verifications': pending_verifications,
            'total_orders': total_orders,
            'active_orders': active_orders,
            'ready_for_pickup': ready_for_pickup,
            'school_name': school.name,
        })
