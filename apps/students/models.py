from django.db import models
from apps.users.models import CustomUser
from apps.schools.models import School


class VerificationStatus(models.TextChoices):
    PENDING  = 'pending',  'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


class GenderChoices(models.TextChoices):
    MALE = 'male', 'Male'
    FEMALE = 'female', 'Female'
    OTHER = 'other', 'Other'

class StudentProfile(models.Model):
    """
    A parent/guardian user can manage multiple student profiles.
    Each StudentProfile represents one student under one school.
    """
    parent = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='student_profiles'
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='students')
    student_name   = models.CharField(max_length=255)
    gender         = models.CharField(max_length=10, choices=GenderChoices.choices, default=GenderChoices.MALE)
    class_name     = models.CharField(max_length=50)    # e.g. "Grade 5"
    section        = models.CharField(max_length=10, blank=True)
    roll_number    = models.CharField(max_length=50, blank=True)
    student_id     = models.CharField(max_length=100, blank=True)   # School-issued ID
    id_card_attachment = models.ImageField(upload_to='student_profiles/id_cards/', blank=True, null=True)
    is_verified    = models.BooleanField(default=False)
    verified_at    = models.DateTimeField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table     = 'student_profiles'
        unique_together = ('school', 'roll_number')

    def __str__(self):
        return f'{self.student_name} — {self.school.name}'


class VerificationRequest(models.Model):
    """Student submits a verification request; school reviews it."""
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name='verification_requests'
    )
    status          = models.CharField(max_length=20, choices=VerificationStatus.choices,
                                       default=VerificationStatus.PENDING)
    request_note    = models.TextField(blank=True)   # Student's note
    # Optional ID card image the student attaches for identity proof
    id_card         = models.ImageField(
        upload_to='verification/id_cards/', blank=True, null=True
    )
    review_note     = models.TextField(blank=True)   # School's response
    reviewed_by     = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'student_verification_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f'VerifyReq: {self.student.student_name} [{self.status}]'
