from django.contrib.contenttypes.models import ContentType
from typing import List, Optional, Union
from django.contrib.auth import get_user_model

from accounts.models import (
    User,
    Notification
)


class NotificationFactory:
    """
    Factory class for creating different types of notifications    
    """
    @classmethod
    def for_welcome_an_user_from_system(cls , targetuser:User) -> Notification:
        """
            Create a Function For An User 
            With No Sender Just System send it
        """

        new_notif = Notification(
            sender=None,
            receiver=targetuser,
            subject=f"پیام خوش آمد",
            text=cls._truncate_text(
                f"کاربر {cls._get_user_display_name(targetuser)} به سامانه اضافه شد",
            ),
        )

        new_notif.save()
        return new_notif



    @classmethod
    def for_comment(cls, comment:Comment, exclude_users: List = None) -> List[Notification]:
        """
        Create notifications when a new comment is posted
        
        Args:
            comment: Comment instance
            exclude_users: List of users to exclude from notifications
            
        Returns:
            List of created notification instances
        """
        notifications = []
        exclude_users = exclude_users or []
        
        # Get all users with access to this ShrhLayer
        eligible_users = comment.sharhlayer.accessible_by_users.exclude(
            id=comment.writer.id  # Don't notify the comment writer
        )
        
        # Exclude additional users if specified
        if exclude_users:
            exclude_ids = [user.id if hasattr(user, 'id') else user for user in exclude_users]
            eligible_users = eligible_users.exclude(id__in=exclude_ids)
        
        # Create notifications for all eligible users
        notifications_to_create = []
        for user in eligible_users:
            notifications_to_create.append(
                Notification(
                    sender=comment.writer,
                    receiver=user,
                    subject=f"نظر جدید در {comment.sharhlayer}",
                    text=cls._truncate_text(
                        f"کاربر {cls._get_user_display_name(comment.writer)} نظری جدید نوشت",
                    ),
                )
            )
        
        # Batch create for better performance
        if notifications_to_create:
            notifications = Notification.objects.bulk_create(notifications_to_create)
        
        return notifications
    
    @classmethod
    def for_reply(cls, reply:Comment) -> List[Notification]:
        """
        Create notifications when someone replies to a comment
        
        Args:
            reply: Comment instance that is a reply
            
        Returns:
            List of created notification instances
        """
        notifications = []
        
        if not reply.parent:
            return notifications  # Not a reply
        
        # Notify the original comment writer (if different from reply writer)
        if reply.parent.writer != reply.writer:
            notification = Notification.objects.create(
                sender=reply.writer,
                receiver=reply.parent.writer,
                subject="پاسخ به نظر شما",
                text=cls._truncate_text(
                    f"{cls._get_user_display_name(reply.writer)} به نظر شما پاسخ داد",
                ),
            )
            notifications.append(notification)
        
        return notifications
    
    @classmethod
    def for_layer_upload(cls , sharhlayer:ShrhLayer, uploader_user: User, exclude_users: List = None) -> List[Notification]:
        """
        Create notifications when a Layer Uploaded
        
        Args:
            sharhlayer: ShrhLayer instance
            exclude_users: List of users to exclude from notifications
            
        Returns:
            List of created notification instances
        """
        notifications = []
        exclude_users = exclude_users or []
        
        # Get all users with access to this ShrhLayer
        eligible_users = sharhlayer.accessible_by_users.exclude(id=uploader_user.id)
        
        # Exclude additional users if specified
        if exclude_users:
            exclude_ids = [user.id if hasattr(user, 'id') else user for user in exclude_users]
            eligible_users = eligible_users.exclude(id__in=exclude_ids)
        
        # Create notifications for all eligible users
        notifications_to_create = []
        for user in eligible_users:
            # Build the notification text with proper error handling
            try:
                layer_name_fa = getattr(sharhlayer.layer_name, 'layername_fa', 'نامشخص')
                layer_name_en = getattr(sharhlayer.layer_name, 'layername_en', 'Unknown')
                layer_group_fa = getattr(sharhlayer.layer_name, 'lyrgroup_fa', 'نامشخص')
                contract_title = getattr(sharhlayer.shrh_base.contract, 'title', 'نامشخص')
                
                notification_text = (
                    f"{cls._get_user_display_name(uploader_user)} لایه {layer_name_fa} "
                    f"({layer_name_en}) برای گروه لایه {layer_group_fa} "
                    f"در قرارداد {contract_title} با موفقیت بارگذاری کرد"
                )
                
            except AttributeError as e:
                # Fallback text if some attributes are missing
                notification_text = (
                    f"{cls._get_user_display_name(uploader_user)} لایه‌ای جدید "
                    f"در {sharhlayer} بارگذاری کرد"
                )
            
            notifications_to_create.append(
                Notification(
                    sender=uploader_user,
                    receiver=user,
                    subject=f"بارگذاری لایه جدید: {layer_name_fa}",  # Shortened subject
                    text=cls._truncate_text(notification_text, max_length=200),
                )
            )
        
        # Batch create for better performance
        if notifications_to_create:
            notifications = Notification.objects.bulk_create(notifications_to_create)
        
        return notifications


    @staticmethod
    def _get_user_display_name(user) -> str:
        """Get the best display name for a user"""
        if user.first_name_fa and user.last_name_fa:
            return f"{user.first_name_fa} {user.last_name_fa}"
        elif user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        else:
            return user.username
    
    @staticmethod
    def _truncate_text(text: str, max_length: int = 1999) -> str:
        """Truncate text to specified length"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."