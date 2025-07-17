from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserProfile, ApplicationTag  # ApplicationTag importieren

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'userprofile'):
        profile = UserProfile.objects.create(user=instance)

        # Standard-Tag setzen (mit "-" als kein Zugriff)
        default_tag, _ = ApplicationTag.objects.get_or_create(name="-")
        profile.tags.add(default_tag)
