from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser, UserRole


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label='Confirm Password')
    role = serializers.ChoiceField(
        choices=[UserRole.STUDENT],
        default=UserRole.STUDENT
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'phone', 'role', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        return CustomUser.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['email'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Invalid credentials.')
        if not user.is_active:
            raise serializers.ValidationError('Account is disabled.')
        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'first_name', 'last_name', 'phone', 'role', 'is_active', 'created_at',
                  'can_manage_vendors', 'can_manage_schools', 'can_manage_students', 'can_manage_content', 'can_manage_reports')
        read_only_fields = ('id', 'role', 'created_at')


class TokenResponseSerializer(serializers.Serializer):
    """Response serializer for login / register."""
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()

    @staticmethod
    def get_tokens_for_user(user):
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }


from .firebase import verify_firebase_token
import random
import string

class OTPLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True)

    def validate(self, attrs):
        id_token = attrs.get('id_token')
        try:
            decoded_token = verify_firebase_token(id_token)
            phone = decoded_token.get('phone_number')
            if not phone:
                raise serializers.ValidationError('No phone number found in Firebase token.')
            
            # Find user by phone
            # We might want to remove spaces or format the phone number if needed
            user = CustomUser.objects.filter(phone=phone).first()
            if not user:
                raise serializers.ValidationError('No account exists with this phone number. Please sign up.')
            
            if not user.is_active:
                raise serializers.ValidationError('Account is disabled.')
                
            attrs['user'] = user
            return attrs
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class OTPSignupSerializer(serializers.ModelSerializer):
    id_token = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    role = serializers.ChoiceField(
        choices=[UserRole.STUDENT],
        default=UserRole.STUDENT
    )

    class Meta:
        model = CustomUser
        fields = ('id_token', 'email', 'first_name', 'last_name', 'role', 'password')

    def validate(self, attrs):
        id_token = attrs.get('id_token')
        email = attrs.get('email')
        
        try:
            decoded_token = verify_firebase_token(id_token)
            phone = decoded_token.get('phone_number')
            if not phone:
                raise serializers.ValidationError('No phone number found in Firebase token.')
            
            # Check phone uniqueness
            if CustomUser.objects.filter(phone=phone).exists():
                raise serializers.ValidationError({'phone': 'A user with this phone number already exists.'})
                
            # Check email uniqueness
            if CustomUser.objects.filter(email=email).exists():
                raise serializers.ValidationError({'email': 'A user with this email address already exists.'})
                
            attrs['phone'] = phone
            return attrs
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def create(self, validated_data):
        validated_data.pop('id_token')
        password = validated_data.pop('password', None)
        
        # If no password provided, generate a random one
        if not password:
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            
        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user


class OTPForgotPasswordSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
            
        id_token = attrs.get('id_token')
        try:
            decoded_token = verify_firebase_token(id_token)
            phone = decoded_token.get('phone_number')
            if not phone:
                raise serializers.ValidationError('No phone number found in Firebase token.')
            
            user = CustomUser.objects.filter(phone=phone).first()
            if not user:
                raise serializers.ValidationError('No account exists with this phone number.')
                
            attrs['user'] = user
            return attrs
        except ValueError as e:
            raise serializers.ValidationError(str(e))


from .models import ContactLead

class ContactLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactLead
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


# ─── Email magic-link OTP serializers ────────────────────────────────────────

class EmailOTPLoginSerializer(serializers.Serializer):
    """Login via Firebase email sign-in link — looks up user by email in the token."""
    id_token = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            decoded = verify_firebase_token(attrs['id_token'])
            email = decoded.get('email')
            if not email:
                raise serializers.ValidationError('No email found in Firebase token.')
            user = CustomUser.objects.filter(email=email).first()
            if not user:
                raise serializers.ValidationError(
                    'No account found for this email. Please sign up first.'
                )
            if not user.is_active:
                raise serializers.ValidationError('Account is disabled.')
            attrs['user'] = user
            return attrs
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class EmailOTPSignupSerializer(serializers.ModelSerializer):
    """Register via Firebase email sign-in link — email comes from the verified token."""
    id_token   = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(
        choices=[UserRole.STUDENT], default=UserRole.STUDENT
    )

    class Meta:
        model  = CustomUser
        fields = ('id_token', 'first_name', 'last_name', 'role')

    def validate(self, attrs):
        try:
            decoded = verify_firebase_token(attrs['id_token'])
            email = decoded.get('email')
            if not email:
                raise serializers.ValidationError('No email found in Firebase token.')
            if CustomUser.objects.filter(email=email).exists():
                raise serializers.ValidationError(
                    {'email': 'An account with this email already exists. Please log in.'}
                )
            attrs['email'] = email
            return attrs
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def create(self, validated_data):
        validated_data.pop('id_token')
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        return CustomUser.objects.create_user(password=password, **validated_data)


class EmailOTPForgotPasswordSerializer(serializers.Serializer):
    """Reset password after verifying via Firebase email sign-in link."""
    id_token  = serializers.CharField(write_only=True)
    password  = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        try:
            decoded = verify_firebase_token(attrs['id_token'])
            email = decoded.get('email')
            if not email:
                raise serializers.ValidationError('No email found in Firebase token.')
            user = CustomUser.objects.filter(email=email).first()
            if not user:
                raise serializers.ValidationError('No account found for this email.')
            attrs['user'] = user
            return attrs
        except ValueError as e:
            raise serializers.ValidationError(str(e))
