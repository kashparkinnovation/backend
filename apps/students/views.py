import csv
import io
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import StudentProfile, VerificationRequest, VerificationStatus
from .serializers import (
    StudentProfileSerializer,
    VerificationRequestSerializer,
    VerificationRequestCreateSerializer,
    VerificationRequestActionSerializer,
)
from apps.users.permissions import IsStudent, IsSchool
from rest_framework.permissions import IsAuthenticated


# ─── Student Profile Views ────────────────────────────────────────────────────

class StudentProfileListCreateView(generics.ListCreateAPIView):
    """
    Student/parent: list and create their own student profiles.
    School: list ALL students belonging to their school.
    """
    serializer_class = StudentProfileSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsStudent()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'student':
            return StudentProfile.objects.filter(parent=user).select_related('school')
        elif user.role == 'school':
            school = getattr(user, 'school_profile', None)
            if school:
                return (
                    StudentProfile.objects
                    .filter(school=school)
                    .select_related('school', 'parent')
                    .prefetch_related('verification_requests')
                )
        return StudentProfile.objects.none()

    def perform_create(self, serializer):
        profile = serializer.save(parent=self.request.user)
        # Auto-create verification request so school can verify them
        from .models import VerificationRequest
        VerificationRequest.objects.create(
            student=profile,
            request_note="Auto-submitted during profile creation.",
            id_card=profile.id_card_attachment if profile.id_card_attachment else None
        )


class StudentProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE a student profile — owner or school only."""
    serializer_class = StudentProfileSerializer

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'student':
            return StudentProfile.objects.filter(parent=user)
        elif user.role == 'school':
            school = getattr(user, 'school_profile', None)
            if school:
                return StudentProfile.objects.filter(school=school)
        return StudentProfile.objects.none()


# ─── Verification Request Views ───────────────────────────────────────────────

class VerificationRequestCreateView(APIView):
    """POST /api/v1/students/verify-request/ — Student submits a verification request."""
    permission_classes = [IsStudent]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = VerificationRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student = get_object_or_404(StudentProfile, pk=serializer.validated_data['student'].id, parent=request.user)

        # Prevent duplicate pending requests
        if VerificationRequest.objects.filter(student=student, status=VerificationStatus.PENDING).exists():
            return Response({'detail': 'A pending verification request already exists.'}, status=400)

        vr = VerificationRequest.objects.create(
            student      = student,
            request_note = serializer.validated_data.get('request_note', ''),
            id_card      = serializer.validated_data.get('id_card', None),
        )
        return Response(VerificationRequestSerializer(vr).data, status=status.HTTP_201_CREATED)


class SchoolVerificationQueueView(generics.ListAPIView):
    """GET /api/v1/students/school/verification-requests/ — School sees all requests for their students."""
    serializer_class = VerificationRequestSerializer
    permission_classes = [IsSchool]
    filterset_fields = ['status']

    def get_queryset(self):
        school = getattr(self.request.user, 'school_profile', None)
        if not school:
            return VerificationRequest.objects.none()
        qs = (
            VerificationRequest.objects
            .filter(student__school=school)
            .select_related('student', 'student__school', 'student__parent', 'reviewed_by')
        )
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class SchoolVerificationActionView(APIView):
    """PATCH /api/v1/students/school/verification-requests/{id}/action/ — Approve or reject."""
    permission_classes = [IsSchool]

    def patch(self, request, pk):
        school = getattr(request.user, 'school_profile', None)
        vr = get_object_or_404(VerificationRequest, pk=pk, student__school=school)

        serializer = VerificationRequestActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action      = serializer.validated_data['action']
        review_note = serializer.validated_data.get('review_note', '')

        vr.status      = VerificationStatus.APPROVED if action == 'approve' else VerificationStatus.REJECTED
        vr.review_note = review_note
        vr.reviewed_by = request.user
        vr.reviewed_at = timezone.now()
        vr.save()

        # If approved, also mark the student as verified
        if action == 'approve':
            vr.student.is_verified = True
            vr.student.verified_at = timezone.now()
            vr.student.save(update_fields=['is_verified', 'verified_at'])

        return Response(VerificationRequestSerializer(vr).data)


class AdminVerificationQueueView(generics.ListAPIView):
    """GET /api/v1/students/admin/verification-requests/ — Admin sees all student requests globally."""
    serializer_class = VerificationRequestSerializer
    from apps.users.permissions import IsAdmin
    permission_classes = [IsAdmin]
    filterset_fields = ['status']

    def get_queryset(self):
        qs = VerificationRequest.objects.select_related(
            'student', 'student__school', 'student__parent', 'reviewed_by'
        ).order_by('-created_at')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

class AdminVerificationActionView(APIView):
    """PATCH /api/v1/students/admin/verification-requests/{id}/action/ — Admin approves or rejects."""
    from apps.users.permissions import IsAdmin
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        vr = get_object_or_404(VerificationRequest, pk=pk)

        serializer = VerificationRequestActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action      = serializer.validated_data['action']
        review_note = serializer.validated_data.get('review_note', '')

        vr.status      = VerificationStatus.APPROVED if action == 'approve' else VerificationStatus.REJECTED
        vr.review_note = review_note
        vr.reviewed_by = request.user
        vr.reviewed_at = timezone.now()
        vr.save()

        # If approved, also mark the student as verified
        if action == 'approve':
            vr.student.is_verified = True
            vr.student.verified_at = timezone.now()
            vr.student.save(update_fields=['is_verified', 'verified_at'])

        return Response(VerificationRequestSerializer(vr).data)


# ─── Legacy direct verify (admin shortcut) ───────────────────────────────────

class StudentVerifyView(APIView):
    """POST /api/v1/students/{id}/verify/ — School directly verifies a student (no request needed)."""
    permission_classes = [IsSchool]

    def post(self, request, pk):
        school = getattr(request.user, 'school_profile', None)
        student = get_object_or_404(StudentProfile, pk=pk, school=school)
        student.is_verified = True
        student.verified_at = timezone.now()
        student.save(update_fields=['is_verified', 'verified_at'])
        return Response(StudentProfileSerializer(student).data)


class StudentUnverifyView(APIView):
    """POST /api/v1/students/{id}/unverify/ — School revokes verification."""
    permission_classes = [IsSchool]

    def post(self, request, pk):
        school = getattr(request.user, 'school_profile', None)
        student = get_object_or_404(StudentProfile, pk=pk, school=school)
        student.is_verified = False
        student.verified_at = None
        student.save(update_fields=['is_verified', 'verified_at'])
        return Response(StudentProfileSerializer(student).data)


# ─── CSV Import ───────────────────────────────────────────────────────────────

class StudentCSVImportView(APIView):
    """
    POST /api/v1/students/school/import/
    Columns: student_name, class_name, section, roll_number, student_id, parent_email
    """
    permission_classes = [IsSchool]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request):
        school = getattr(request.user, 'school_profile', None)
        if not school:
            return Response({'detail': 'No school profile found.'}, status=403)

        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({'detail': 'No file uploaded.'}, status=400)

        decoded = csv_file.read().decode('utf-8-sig')
        reader  = csv.DictReader(io.StringIO(decoded))

        created_count = 0
        skipped_count = 0
        errors        = []

        from apps.users.models import CustomUser, UserRole
        from django.contrib.auth.hashers import make_password

        for i, row in enumerate(reader, start=2):
            try:
                roll   = (row.get('roll_number') or '').strip()
                name   = (row.get('student_name') or '').strip()
                email  = (row.get('parent_email') or '').strip()
                clname = (row.get('class_name') or '').strip()
                sec    = (row.get('section') or '').strip()
                sid    = (row.get('student_id') or '').strip()

                if not name or not roll:
                    errors.append({'row': i, 'error': 'student_name and roll_number are required'})
                    continue

                # Get or create parent user
                if email:
                    parent, _ = CustomUser.objects.get_or_create(
                        email=email,
                        defaults={
                            'first_name': name.split()[0],
                            'last_name':  name.split()[-1] if len(name.split()) > 1 else '',
                            'role':     UserRole.STUDENT,
                            'password': make_password('changeme123'),
                        }
                    )
                else:
                    # Create a placeholder parent without email
                    parent, _ = CustomUser.objects.get_or_create(
                        email=f'student_{roll}_{school.code}@placeholder.in',
                        defaults={
                            'first_name': name.split()[0],
                            'role':       UserRole.STUDENT,
                            'password':   make_password('changeme123'),
                        }
                    )

                profile, created = StudentProfile.objects.get_or_create(
                    school=school,
                    roll_number=roll,
                    defaults={
                        'parent':       parent,
                        'student_name': name,
                        'class_name':   clname,
                        'section':      sec,
                        'student_id':   sid,
                        'is_verified':  True,          # CSV import = pre-verified
                        'verified_at':  timezone.now(),
                    }
                )
                if created:
                    created_count += 1
                else:
                    skipped_count += 1

            except Exception as exc:
                errors.append({'row': i, 'error': str(exc)})

        return Response({
            'created': created_count,
            'skipped': skipped_count,
            'errors':  errors,
        }, status=status.HTTP_201_CREATED)
