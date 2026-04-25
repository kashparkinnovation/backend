from rest_framework import serializers
from .models import StudentProfile, VerificationRequest, VerificationStatus


class StudentProfileSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    parent_email = serializers.CharField(source='parent.email', read_only=True)
    pending_verification = serializers.SerializerMethodField()
    latest_verification_request = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = (
            'id', 'parent', 'parent_email', 'school', 'school_name',
            'student_name', 'gender', 'class_name', 'section', 'roll_number',
            'student_id', 'id_card_attachment', 'is_verified', 'verified_at',
            'pending_verification', 'latest_verification_request', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'parent', 'is_verified', 'verified_at', 'created_at', 'updated_at')

    def get_pending_verification(self, obj):
        return obj.verification_requests.filter(status=VerificationStatus.PENDING).exists()

    def get_latest_verification_request(self, obj):
        latest = obj.verification_requests.order_by('-created_at').first()
        if latest:
            return {
                'status': latest.status,
                'request_note': latest.request_note,
                'review_note': latest.review_note,
                'created_at': latest.created_at
            }
        return None


class StudentProfileBriefSerializer(serializers.ModelSerializer):
    """Lightweight serializer for embedding in orders and verification requests."""
    school_name = serializers.CharField(source='school.name', read_only=True)

    class Meta:
        model = StudentProfile
        fields = ('id', 'student_name', 'class_name', 'section', 'roll_number', 'school_name', 'is_verified')


class VerificationRequestSerializer(serializers.ModelSerializer):
    student = StudentProfileBriefSerializer(read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)

    class Meta:
        model = VerificationRequest
        fields = (
            'id', 'student', 'status', 'request_note', 'id_card',
            'review_note', 'reviewed_by', 'reviewed_by_name',
            'reviewed_at', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'student', 'reviewed_by', 'reviewed_at', 'created_at', 'updated_at')


class VerificationRequestCreateSerializer(serializers.ModelSerializer):
    """Used by students when submitting a verification request (supports file upload)."""
    class Meta:
        model = VerificationRequest
        fields = ('student', 'request_note', 'id_card')


class VerificationRequestActionSerializer(serializers.Serializer):
    action      = serializers.ChoiceField(choices=['approve', 'reject'])
    review_note = serializers.CharField(required=False, allow_blank=True)
