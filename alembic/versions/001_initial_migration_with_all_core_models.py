"""Initial migration with all core models

Revision ID: 001
Revises: 
Create Date: 2025-01-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE userrole AS ENUM ('pet_owner', 'veterinarian', 'vet_tech', 'clinic_admin', 'platform_admin')")
    op.execute("CREATE TYPE userstatus AS ENUM ('active', 'inactive', 'suspended', 'pending_verification')")
    op.execute("CREATE TYPE petspecies AS ENUM ('dog', 'cat', 'bird', 'rabbit', 'hamster', 'guinea_pig', 'ferret', 'reptile', 'fish', 'other')")
    op.execute("CREATE TYPE petgender AS ENUM ('male', 'female', 'unknown')")
    op.execute("CREATE TYPE petsize AS ENUM ('extra_small', 'small', 'medium', 'large', 'extra_large')")
    op.execute("CREATE TYPE petstatus AS ENUM ('active', 'inactive', 'deceased', 'lost', 'transferred')")
    op.execute("CREATE TYPE appointmentstatus AS ENUM ('scheduled', 'confirmed', 'checked_in', 'in_progress', 'completed', 'cancelled', 'no_show', 'rescheduled')")
    op.execute("CREATE TYPE servicetype AS ENUM ('wellness_exam', 'vaccination', 'dental_cleaning', 'surgery', 'emergency', 'grooming', 'boarding', 'consultation', 'follow_up', 'diagnostic', 'treatment', 'other')")
    op.execute("CREATE TYPE appointmentpriority AS ENUM ('low', 'normal', 'high', 'urgent', 'emergency')")
    op.execute("CREATE TYPE clinicstatus AS ENUM ('active', 'inactive', 'temporarily_closed', 'permanently_closed', 'under_renovation')")
    op.execute("CREATE TYPE clinictype AS ENUM ('general_practice', 'emergency', 'specialty', 'mobile', 'hospital', 'urgent_care')")
    op.execute("CREATE TYPE veterinarianstatus AS ENUM ('active', 'inactive', 'on_leave', 'suspended', 'retired')")
    op.execute("CREATE TYPE licensestatus AS ENUM ('active', 'expired', 'suspended', 'revoked', 'pending_renewal')")
    op.execute("CREATE TYPE employmenttype AS ENUM ('full_time', 'part_time', 'contract', 'locum', 'owner', 'partner')")

    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('clerk_user_id', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('role', sa.Enum('pet_owner', 'veterinarian', 'vet_tech', 'clinic_admin', 'platform_admin', name='userrole'), server_default='pet_owner', nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'suspended', 'pending_verification', name='userstatus'), server_default='pending_verification', nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('email_notifications', sa.Boolean(), nullable=False),
        sa.Column('sms_notifications', sa.Boolean(), nullable=False),
        sa.Column('email_verified', sa.Boolean(), nullable=False),
        sa.Column('phone_verified', sa.Boolean(), nullable=False),
        sa.Column('terms_accepted_at', sa.String(length=50), nullable=True),
        sa.Column('privacy_accepted_at', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('clerk_user_id', name='uq_users_clerk_user_id'),
        sa.UniqueConstraint('email', name='uq_users_email')
    )
    
    # Create indexes for users table
    op.create_index('idx_users_clerk_user_id', 'users', ['clerk_user_id'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_users_status', 'users', ['status'])
    op.create_index('idx_users_role_status', 'users', ['role', 'status'])
    op.create_index('idx_users_email_status', 'users', ['email', 'status'])
    op.create_index('idx_users_name_search', 'users', ['first_name', 'last_name'])
    op.create_index('idx_users_location', 'users', ['city', 'state', 'country'])
    op.create_index('idx_users_preferences_gin', 'users', ['preferences'], postgresql_using='gin')

    # Create clinics table
    op.create_table('clinics',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('license_number', sa.String(length=100), nullable=True),
        sa.Column('type', sa.Enum('general_practice', 'emergency', 'specialty', 'mobile', 'hospital', 'urgent_care', name='clinictype'), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'temporarily_closed', 'permanently_closed', 'under_renovation', name='clinicstatus'), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=False),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('postal_code', sa.String(length=20), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('operating_hours', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=True),
        sa.Column('services_offered', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('specialties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('accepts_new_patients', sa.Boolean(), nullable=False),
        sa.Column('accepts_emergencies', sa.Boolean(), nullable=False),
        sa.Column('accepts_walk_ins', sa.Boolean(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('facility_features', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('equipment_available', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('max_daily_appointments', sa.Integer(), nullable=True),
        sa.Column('number_of_exam_rooms', sa.Integer(), nullable=True),
        sa.Column('number_of_surgery_rooms', sa.Integer(), nullable=True),
        sa.Column('insurance_accepted', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('payment_methods', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('emergency_contact_number', sa.String(length=20), nullable=True),
        sa.Column('after_hours_instructions', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('photos', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint('latitude IS NULL OR (latitude >= -90 AND latitude <= 90)', name='ck_clinics_latitude_valid'),
        sa.CheckConstraint('longitude IS NULL OR (longitude >= -180 AND longitude <= 180)', name='ck_clinics_longitude_valid'),
        sa.CheckConstraint('max_daily_appointments IS NULL OR max_daily_appointments > 0', name='ck_clinics_max_appointments_positive'),
        sa.CheckConstraint('number_of_exam_rooms IS NULL OR number_of_exam_rooms > 0', name='ck_clinics_exam_rooms_positive'),
        sa.CheckConstraint('number_of_surgery_rooms IS NULL OR number_of_surgery_rooms >= 0', name='ck_clinics_surgery_rooms_non_negative'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('license_number', name='uq_clinics_license_number')
    )
    
    # Create indexes for clinics table
    op.create_index('idx_clinics_name', 'clinics', ['name'])
    op.create_index('idx_clinics_type', 'clinics', ['type'])
    op.create_index('idx_clinics_status', 'clinics', ['status'])
    op.create_index('idx_clinics_city', 'clinics', ['city'])
    op.create_index('idx_clinics_state', 'clinics', ['state'])
    op.create_index('idx_clinics_country', 'clinics', ['country'])
    op.create_index('idx_clinics_postal_code', 'clinics', ['postal_code'])
    op.create_index('idx_clinics_location', 'clinics', ['city', 'state', 'country'])
    op.create_index('idx_clinics_status_type', 'clinics', ['status', 'type'])
    op.create_index('idx_clinics_accepts_new_patients', 'clinics', ['accepts_new_patients', 'status'])
    op.create_index('idx_clinics_accepts_emergencies', 'clinics', ['accepts_emergencies', 'status'])
    op.create_index('idx_clinics_accepts_walk_ins', 'clinics', ['accepts_walk_ins', 'status'])
    op.create_index('idx_clinics_coordinates', 'clinics', ['latitude', 'longitude'], postgresql_where='latitude IS NOT NULL AND longitude IS NOT NULL')
    op.create_index('idx_clinics_operating_hours_gin', 'clinics', ['operating_hours'], postgresql_using='gin')
    op.create_index('idx_clinics_services_offered_gin', 'clinics', ['services_offered'], postgresql_using='gin')
    op.create_index('idx_clinics_specialties_gin', 'clinics', ['specialties'], postgresql_using='gin')

    # Create veterinarians table
    op.create_table('veterinarians',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('license_number', sa.String(length=100), nullable=False),
        sa.Column('license_state', sa.String(length=100), nullable=False),
        sa.Column('license_country', sa.String(length=100), nullable=False),
        sa.Column('license_status', sa.Enum('active', 'expired', 'suspended', 'revoked', 'pending_renewal', name='licensestatus'), nullable=False),
        sa.Column('license_issued_date', sa.Date(), nullable=True),
        sa.Column('license_expiry_date', sa.Date(), nullable=True),
        sa.Column('veterinary_school', sa.String(length=200), nullable=True),
        sa.Column('graduation_year', sa.Integer(), nullable=True),
        sa.Column('degree_type', sa.String(length=50), nullable=True),
        sa.Column('additional_certifications', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.Enum('active', 'inactive', 'on_leave', 'suspended', 'retired', name='veterinarianstatus'), nullable=False),
        sa.Column('employment_type', sa.Enum('full_time', 'part_time', 'contract', 'locum', 'owner', 'partner', name='employmenttype'), nullable=False),
        sa.Column('years_of_experience', sa.Integer(), nullable=False),
        sa.Column('hire_date', sa.Date(), nullable=True),
        sa.Column('specializations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('services_provided', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('species_expertise', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('availability', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_accepting_new_patients', sa.Boolean(), nullable=False),
        sa.Column('appointment_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('max_daily_appointments', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('total_reviews', sa.Integer(), nullable=False),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('professional_interests', sa.Text(), nullable=True),
        sa.Column('languages_spoken', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('emergency_contact_number', sa.String(length=20), nullable=True),
        sa.Column('professional_memberships', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint('years_of_experience >= 0', name='ck_veterinarians_experience_non_negative'),
        sa.CheckConstraint('graduation_year IS NULL OR graduation_year > 1800', name='ck_veterinarians_graduation_year_valid'),
        sa.CheckConstraint('rating >= 0 AND rating <= 5', name='ck_veterinarians_rating_valid'),
        sa.CheckConstraint('total_reviews >= 0', name='ck_veterinarians_reviews_non_negative'),
        sa.CheckConstraint('appointment_duration_minutes IS NULL OR appointment_duration_minutes > 0', name='ck_veterinarians_appointment_duration_positive'),
        sa.CheckConstraint('max_daily_appointments IS NULL OR max_daily_appointments > 0', name='ck_veterinarians_max_appointments_positive'),
        sa.CheckConstraint('license_issued_date IS NULL OR license_issued_date <= CURRENT_DATE', name='ck_veterinarians_license_issued_not_future'),
        sa.CheckConstraint('license_expiry_date IS NULL OR license_expiry_date > license_issued_date', name='ck_veterinarians_license_expiry_after_issued'),
        sa.CheckConstraint('hire_date IS NULL OR hire_date <= CURRENT_DATE', name='ck_veterinarians_hire_date_not_future'),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('license_number', name='uq_veterinarians_license_number'),
        sa.UniqueConstraint('user_id', name='uq_veterinarians_user_id')
    )
    
    # Create indexes for veterinarians table
    op.create_index('idx_veterinarians_user_id', 'veterinarians', ['user_id'])
    op.create_index('idx_veterinarians_clinic_id', 'veterinarians', ['clinic_id'])
    op.create_index('idx_veterinarians_license_number', 'veterinarians', ['license_number'])
    op.create_index('idx_veterinarians_status', 'veterinarians', ['status'])
    op.create_index('idx_veterinarians_license_status', 'veterinarians', ['license_status'])
    op.create_index('idx_veterinarians_employment_type', 'veterinarians', ['employment_type'])
    op.create_index('idx_veterinarians_is_accepting_new_patients', 'veterinarians', ['is_accepting_new_patients'])
    op.create_index('idx_veterinarians_rating', 'veterinarians', ['rating'])
    op.create_index('idx_veterinarians_license_expiry_date', 'veterinarians', ['license_expiry_date'])
    op.create_index('idx_veterinarians_clinic_status', 'veterinarians', ['clinic_id', 'status'])
    op.create_index('idx_veterinarians_specializations_gin', 'veterinarians', ['specializations'], postgresql_using='gin')
    op.create_index('idx_veterinarians_services_gin', 'veterinarians', ['services_provided'], postgresql_using='gin')
    op.create_index('idx_veterinarians_species_gin', 'veterinarians', ['species_expertise'], postgresql_using='gin')

    # Create pets table
    op.create_table('pets',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('species', sa.Enum('dog', 'cat', 'bird', 'rabbit', 'hamster', 'guinea_pig', 'ferret', 'reptile', 'fish', 'other', name='petspecies'), nullable=False),
        sa.Column('species_other_description', sa.String(length=100), nullable=True),
        sa.Column('breed', sa.String(length=100), nullable=True),
        sa.Column('mixed_breed', sa.Boolean(), nullable=False),
        sa.Column('gender', sa.Enum('male', 'female', 'unknown', name='petgender'), nullable=False),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('approximate_age_years', sa.Integer(), nullable=True),
        sa.Column('approximate_age_months', sa.Integer(), nullable=True),
        sa.Column('weight_kg', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('size_category', sa.Enum('extra_small', 'small', 'medium', 'large', 'extra_large', name='petsize'), nullable=True),
        sa.Column('microchip_id', sa.String(length=50), nullable=True),
        sa.Column('registration_number', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('active', 'inactive', 'deceased', 'lost', 'transferred', name='petstatus'), nullable=False),
        sa.Column('is_spayed_neutered', sa.Boolean(), nullable=False),
        sa.Column('spay_neuter_date', sa.Date(), nullable=True),
        sa.Column('is_microchipped', sa.Boolean(), nullable=False),
        sa.Column('microchip_date', sa.Date(), nullable=True),
        sa.Column('is_insured', sa.Boolean(), nullable=False),
        sa.Column('insurance_provider', sa.String(length=100), nullable=True),
        sa.Column('insurance_policy_number', sa.String(length=100), nullable=True),
        sa.Column('temperament', sa.String(length=200), nullable=True),
        sa.Column('special_needs', sa.Text(), nullable=True),
        sa.Column('behavioral_notes', sa.Text(), nullable=True),
        sa.Column('profile_photo_url', sa.String(length=500), nullable=True),
        sa.Column('additional_photos', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('medical_history', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('vaccination_records', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('medication_history', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('allergy_information', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('emergency_contact', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('preferred_veterinarian_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('preferred_clinic_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint('weight_kg IS NULL OR weight_kg > 0', name='ck_pets_weight_positive'),
        sa.CheckConstraint("species != 'other' OR species_other_description IS NOT NULL", name='ck_pets_species_other_description_required'),
        sa.CheckConstraint('approximate_age_years IS NULL OR approximate_age_years >= 0', name='ck_pets_age_years_non_negative'),
        sa.CheckConstraint('approximate_age_months IS NULL OR (approximate_age_months >= 0 AND approximate_age_months < 12)', name='ck_pets_age_months_valid'),
        sa.CheckConstraint('birth_date IS NULL OR birth_date <= CURRENT_DATE', name='ck_pets_birth_date_not_future'),
        sa.CheckConstraint('spay_neuter_date IS NULL OR spay_neuter_date <= CURRENT_DATE', name='ck_pets_spay_neuter_date_not_future'),
        sa.CheckConstraint('microchip_date IS NULL OR microchip_date <= CURRENT_DATE', name='ck_pets_microchip_date_not_future'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['preferred_clinic_id'], ['clinics.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['preferred_veterinarian_id'], ['veterinarians.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('microchip_id')
    )
    
    # Create indexes for pets table
    op.create_index('idx_pets_owner_id', 'pets', ['owner_id'])
    op.create_index('idx_pets_species', 'pets', ['species'])
    op.create_index('idx_pets_breed', 'pets', ['breed'])
    op.create_index('idx_pets_status', 'pets', ['status'])
    op.create_index('idx_pets_microchip_id', 'pets', ['microchip_id'])
    op.create_index('idx_pets_preferred_veterinarian_id', 'pets', ['preferred_veterinarian_id'])
    op.create_index('idx_pets_preferred_clinic_id', 'pets', ['preferred_clinic_id'])
    op.create_index('idx_pets_owner_name', 'pets', ['owner_id', 'name'])
    op.create_index('idx_pets_owner_species', 'pets', ['owner_id', 'species'])
    op.create_index('idx_pets_owner_status', 'pets', ['owner_id', 'status'])
    op.create_index('idx_pets_species_breed', 'pets', ['species', 'breed'])
    op.create_index('idx_pets_medical_history_gin', 'pets', ['medical_history'], postgresql_using='gin')
    op.create_index('idx_pets_vaccination_records_gin', 'pets', ['vaccination_records'], postgresql_using='gin')

    # Create appointments table
    op.create_table('appointments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('pet_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('veterinarian_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('service_type', sa.Enum('wellness_exam', 'vaccination', 'dental_cleaning', 'surgery', 'emergency', 'grooming', 'boarding', 'consultation', 'follow_up', 'diagnostic', 'treatment', 'other', name='servicetype'), nullable=False),
        sa.Column('service_type_other_description', sa.String(length=200), nullable=True),
        sa.Column('status', sa.Enum('scheduled', 'confirmed', 'checked_in', 'in_progress', 'completed', 'cancelled', 'no_show', 'rescheduled', name='appointmentstatus'), nullable=False),
        sa.Column('priority', sa.Enum('low', 'normal', 'high', 'urgent', 'emergency', name='appointmentpriority'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        sa.Column('estimated_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('actual_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('checked_in_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.String(length=500), nullable=True),
        sa.Column('follow_up_needed', sa.Boolean(), nullable=True),
        sa.Column('follow_up_instructions', sa.Text(), nullable=True),
        sa.Column('next_appointment_recommended_days', sa.Integer(), nullable=True),
        sa.CheckConstraint('duration_minutes > 0', name='ck_appointments_duration_positive'),
        sa.CheckConstraint("service_type != 'other' OR service_type_other_description IS NOT NULL", name='ck_appointments_service_other_description_required'),
        sa.CheckConstraint('estimated_cost IS NULL OR estimated_cost >= 0', name='ck_appointments_estimated_cost_non_negative'),
        sa.CheckConstraint('actual_cost IS NULL OR actual_cost >= 0', name='ck_appointments_actual_cost_non_negative'),
        sa.CheckConstraint('scheduled_at > created_at', name='ck_appointments_scheduled_after_created'),
        sa.CheckConstraint('checked_in_at IS NULL OR checked_in_at >= created_at', name='ck_appointments_checked_in_after_created'),
        sa.CheckConstraint('started_at IS NULL OR started_at >= created_at', name='ck_appointments_started_after_created'),
        sa.CheckConstraint('completed_at IS NULL OR completed_at >= created_at', name='ck_appointments_completed_after_created'),
        sa.CheckConstraint('cancelled_at IS NULL OR cancelled_at >= created_at', name='ck_appointments_cancelled_after_created'),
        sa.CheckConstraint('next_appointment_recommended_days IS NULL OR next_appointment_recommended_days > 0', name='ck_appointments_next_appointment_days_positive'),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pet_id'], ['pets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['veterinarian_id'], ['veterinarians.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for appointments table
    op.create_index('idx_appointments_pet_id', 'appointments', ['pet_id'])
    op.create_index('idx_appointments_veterinarian_id', 'appointments', ['veterinarian_id'])
    op.create_index('idx_appointments_clinic_id', 'appointments', ['clinic_id'])
    op.create_index('idx_appointments_scheduled_at', 'appointments', ['scheduled_at'])
    op.create_index('idx_appointments_service_type', 'appointments', ['service_type'])
    op.create_index('idx_appointments_status', 'appointments', ['status'])
    op.create_index('idx_appointments_priority', 'appointments', ['priority'])
    op.create_index('idx_appointments_pet_scheduled', 'appointments', ['pet_id', 'scheduled_at'])
    op.create_index('idx_appointments_vet_scheduled', 'appointments', ['veterinarian_id', 'scheduled_at'])
    op.create_index('idx_appointments_clinic_scheduled', 'appointments', ['clinic_id', 'scheduled_at'])
    op.create_index('idx_appointments_status_scheduled', 'appointments', ['status', 'scheduled_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('appointments')
    op.drop_table('pets')
    op.drop_table('veterinarians')
    op.drop_table('clinics')
    op.drop_table('users')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS employmenttype")
    op.execute("DROP TYPE IF EXISTS licensestatus")
    op.execute("DROP TYPE IF EXISTS veterinarianstatus")
    op.execute("DROP TYPE IF EXISTS clinictype")
    op.execute("DROP TYPE IF EXISTS clinicstatus")
    op.execute("DROP TYPE IF EXISTS appointmentpriority")
    op.execute("DROP TYPE IF EXISTS servicetype")
    op.execute("DROP TYPE IF EXISTS appointmentstatus")
    op.execute("DROP TYPE IF EXISTS petstatus")
    op.execute("DROP TYPE IF EXISTS petsize")
    op.execute("DROP TYPE IF EXISTS petgender")
    op.execute("DROP TYPE IF EXISTS petspecies")
    op.execute("DROP TYPE IF EXISTS userstatus")
    op.execute("DROP TYPE IF EXISTS userrole")