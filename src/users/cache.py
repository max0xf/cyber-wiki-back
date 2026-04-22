"""
API response caching utilities.
"""
import logging
from datetime import timedelta
from typing import Any, Optional
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

from .models import APIResponseCache

logger = logging.getLogger(__name__)


# Default cache settings
DEFAULT_CACHE_ENABLED = False
DEFAULT_CACHE_TTL_MINUTES = 5  # 5 minutes default TTL


class APICache:
    """
    Manager for API response caching.
    
    Settings are stored in UserProfile.settings JSONField:
    - cache_enabled: bool (default: False)
    - cache_ttl_minutes: int (default: 5, 0 = never expire)
    """
    
    def __init__(self, user: User):
        self.user = user
        self._profile = None
    
    @property
    def profile(self):
        """Get or create user profile."""
        if self._profile is None:
            from .models import UserProfile
            self._profile, _ = UserProfile.objects.get_or_create(user=self.user)
        return self._profile
    
    def get_settings(self) -> dict:
        """Get cache settings from user profile."""
        settings = self.profile.settings or {}
        return {
            'cache_enabled': settings.get('cache_enabled', DEFAULT_CACHE_ENABLED),
            'cache_ttl_minutes': settings.get('cache_ttl_minutes', DEFAULT_CACHE_TTL_MINUTES),
        }
    
    def update_settings(self, cache_enabled: Optional[bool] = None, cache_ttl_minutes: Optional[int] = None) -> dict:
        """Update cache settings in user profile."""
        settings = self.profile.settings or {}
        
        if cache_enabled is not None:
            settings['cache_enabled'] = cache_enabled
        
        if cache_ttl_minutes is not None:
            settings['cache_ttl_minutes'] = max(0, cache_ttl_minutes)  # Ensure non-negative
        
        self.profile.settings = settings
        self.profile.save(update_fields=['settings'])
        
        return self.get_settings()
    
    def is_enabled(self) -> bool:
        """Check if cache is enabled."""
        return self.get_settings()['cache_enabled']
    
    def get_ttl_minutes(self) -> int:
        """Get cache TTL in minutes."""
        return self.get_settings()['cache_ttl_minutes']
    
    def get(
        self,
        provider_type: str,
        provider_id: str,
        endpoint: str,
        params: dict,
        method: str = 'GET'
    ) -> Optional[dict]:
        """
        Get cached response if available and not expired.
        
        Returns:
            Cached response data or None if not found/expired
        """
        params_hash = APIResponseCache.compute_params_hash(params)
        
        try:
            cache_entry = APIResponseCache.objects.get(
                user=self.user,
                provider_type=provider_type,
                provider_id=provider_id,
                endpoint=endpoint,
                method=method,
                params_hash=params_hash
            )
            
            # Check TTL
            ttl_minutes = self.get_ttl_minutes()
            if ttl_minutes > 0:
                expiry = cache_entry.created_at + timedelta(minutes=ttl_minutes)
                if timezone.now() > expiry:
                    logger.info(f'Cache expired (TTL={ttl_minutes}min): {endpoint}')
                    return None
            # If TTL is 0, cache never expires
            
            # Update hit count
            cache_entry.hit_count += 1
            cache_entry.save(update_fields=['hit_count'])
            
            logger.info(
                f'Cache HIT: {provider_type}:{endpoint} '
                f'(hits: {cache_entry.hit_count}, age: {(timezone.now() - cache_entry.created_at).total_seconds():.0f}s)'
            )
            
            return {
                'data': cache_entry.response_data,
                'status_code': cache_entry.status_code,
                'from_cache': True,
                'cached_at': cache_entry.created_at.isoformat(),
            }
        
        except APIResponseCache.DoesNotExist:
            logger.info(f'Cache MISS: {provider_type}:{endpoint}')
            return None
    
    def set(
        self,
        provider_type: str,
        provider_id: str,
        endpoint: str,
        params: dict,
        response_data: Any,
        status_code: int = 200,
        method: str = 'GET'
    ) -> None:
        """
        Store response in cache.
        
        Updates the timestamp (created_at) to ensure cache freshness tracking.
        """
        if not self.is_enabled():
            return
        
        params_hash = APIResponseCache.compute_params_hash(params)
        
        try:
            cache_entry, created = APIResponseCache.objects.update_or_create(
                user=self.user,
                provider_type=provider_type,
                provider_id=provider_id,
                endpoint=endpoint,
                method=method,
                params_hash=params_hash,
                defaults={
                    'params_json': params,
                    'response_data': response_data,
                    'status_code': status_code,
                }
            )
            
            # If updating existing entry, manually update created_at to reflect refresh
            if not created:
                cache_entry.created_at = timezone.now()
                cache_entry.save(update_fields=['created_at'])
            
            action = 'Created' if created else 'Refreshed'
            logger.info(
                f'Cache {action}: {provider_type}:{endpoint} '
                f'(hash: {params_hash[:8]}, timestamp: {cache_entry.created_at.isoformat()})'
            )
        
        except Exception as e:
            logger.error(f'Failed to cache response: {e}')
    
    def clear(self, provider_type: Optional[str] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            provider_type: If specified, only clear entries for this provider
            
        Returns:
            Number of entries deleted
        """
        queryset = APIResponseCache.objects.filter(user=self.user)
        
        if provider_type:
            queryset = queryset.filter(provider_type=provider_type)
        
        count = queryset.count()
        queryset.delete()
        
        logger.info(f'Cleared {count} cache entries for {self.user.username}')
        return count
    
    def stats(self) -> dict:
        """Get cache statistics."""
        queryset = APIResponseCache.objects.filter(user=self.user)
        settings = self.get_settings()
        
        return {
            'total_entries': queryset.count(),
            'total_hits': sum(queryset.values_list('hit_count', flat=True)),
            'by_provider': {
                item['provider_type']: item['count']
                for item in queryset.values('provider_type').annotate(
                    count=models.Count('id')
                )
            },
            'cache_enabled': settings['cache_enabled'],
            'cache_ttl_minutes': settings['cache_ttl_minutes'],
        }


def get_cache(user: User) -> APICache:
    """Get API cache instance for user."""
    return APICache(user)
