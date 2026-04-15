"""
Unit tests for cache expiration and edge cases.

Tested Scenarios:
- Cache expiration with TTL
- Cache entry refresh updates created_at
- Cache set error handling
- Cache clear with provider type filter
- Cache never expires with TTL=0

Untested Scenarios / Gaps:
- Cache size limits and eviction
- Concurrent cache access and race conditions
- Cache warming strategies
- Cache statistics aggregation
- Very large response caching
- Cache corruption recovery

Test Strategy:
- Database tests with @pytest.mark.django_db
- Time manipulation for TTL testing
- Error injection for exception handling
- Direct cache API testing
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch

from users.cache import get_cache
from users.models import APIResponseCache


@pytest.mark.django_db
class TestCacheExpiration:
    """Test cache expiration and TTL behavior."""
    
    def test_cache_expires_after_ttl(self, user):
        """Test that cache entries expire after TTL."""
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True, cache_ttl_minutes=5)
        
        # Cache a response
        cache.set(
            provider_type='github',
            provider_id='github.com',
            endpoint='/repos',
            params={},
            response_data={'repos': []},
            status_code=200
        )
        
        # Verify cache hit
        result = cache.get('github', 'github.com', '/repos', {})
        assert result is not None
        assert result['data'] == {'repos': []}
        
        # Simulate time passing beyond TTL
        cache_entry = APIResponseCache.objects.get(
            user=user,
            provider_type='github',
            endpoint='/repos'
        )
        cache_entry.created_at = timezone.now() - timedelta(minutes=10)
        cache_entry.save()
        
        # Cache should be expired
        result = cache.get('github', 'github.com', '/repos', {})
        assert result is None
    
    def test_cache_never_expires_with_zero_ttl(self, user):
        """Test that cache with TTL=0 never expires."""
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True, cache_ttl_minutes=0)
        
        # Cache a response
        cache.set(
            provider_type='github',
            provider_id='github.com',
            endpoint='/repos',
            params={},
            response_data={'repos': []},
            status_code=200
        )
        
        # Simulate time passing (way beyond any reasonable TTL)
        cache_entry = APIResponseCache.objects.get(
            user=user,
            provider_type='github',
            endpoint='/repos'
        )
        cache_entry.created_at = timezone.now() - timedelta(days=365)
        cache_entry.save()
        
        # Cache should still be valid
        result = cache.get('github', 'github.com', '/repos', {})
        assert result is not None
        assert result['data'] == {'repos': []}


@pytest.mark.django_db
class TestCacheRefresh:
    """Test cache entry refresh behavior."""
    
    def test_cache_refresh_updates_created_at(self, user):
        """Test that refreshing cache entry updates created_at timestamp."""
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True, cache_ttl_minutes=60)
        
        # Create initial cache entry
        cache.set(
            provider_type='github',
            provider_id='github.com',
            endpoint='/repos',
            params={},
            response_data={'repos': ['repo1']},
            status_code=200
        )
        
        # Get initial created_at
        cache_entry = APIResponseCache.objects.get(
            user=user,
            provider_type='github',
            endpoint='/repos'
        )
        initial_created_at = cache_entry.created_at
        
        # Wait a bit (simulate time passing)
        import time
        time.sleep(0.1)
        
        # Refresh the cache entry with new data
        cache.set(
            provider_type='github',
            provider_id='github.com',
            endpoint='/repos',
            params={},
            response_data={'repos': ['repo1', 'repo2']},
            status_code=200
        )
        
        # Verify created_at was updated
        cache_entry.refresh_from_db()
        assert cache_entry.created_at > initial_created_at
        assert cache_entry.response_data == {'repos': ['repo1', 'repo2']}


@pytest.mark.django_db
class TestCacheErrorHandling:
    """Test cache error handling."""
    
    def test_cache_set_handles_exceptions_gracefully(self, user):
        """Test that cache.set() handles exceptions without raising."""
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True, cache_ttl_minutes=60)
        
        # Mock update_or_create to raise an exception
        with patch.object(APIResponseCache.objects, 'update_or_create', side_effect=Exception("Database error")):
            # Should not raise exception
            cache.set(
                provider_type='github',
                provider_id='github.com',
                endpoint='/repos',
                params={},
                response_data={'repos': []},
                status_code=200
            )
        
        # Verify no cache entry was created
        assert not APIResponseCache.objects.filter(user=user).exists()


@pytest.mark.django_db
class TestCacheClear:
    """Test cache clearing functionality."""
    
    def test_clear_with_provider_type_filter(self, user):
        """Test clearing cache entries for specific provider."""
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True, cache_ttl_minutes=60)
        
        # Create cache entries for different providers
        cache.set('github', 'github.com', '/repos', {}, {'repos': []}, 200)
        cache.set('github', 'github.com', '/users', {}, {'users': []}, 200)
        cache.set('bitbucket', 'bitbucket.org', '/repos', {}, {'repos': []}, 200)
        cache.set('bitbucket', 'bitbucket.org', '/projects', {}, {'projects': []}, 200)
        
        # Verify all entries exist
        assert APIResponseCache.objects.filter(user=user).count() == 4
        
        # Clear only GitHub entries
        count = cache.clear(provider_type='github')
        
        # Verify only GitHub entries were deleted
        assert count == 2
        assert APIResponseCache.objects.filter(user=user, provider_type='github').count() == 0
        assert APIResponseCache.objects.filter(user=user, provider_type='bitbucket').count() == 2
    
    def test_clear_all_entries(self, user):
        """Test clearing all cache entries."""
        cache = get_cache(user)
        cache.update_settings(cache_enabled=True, cache_ttl_minutes=60)
        
        # Create cache entries for different providers
        cache.set('github', 'github.com', '/repos', {}, {'repos': []}, 200)
        cache.set('bitbucket', 'bitbucket.org', '/repos', {}, {'repos': []}, 200)
        
        # Verify entries exist
        assert APIResponseCache.objects.filter(user=user).count() == 2
        
        # Clear all entries
        count = cache.clear()
        
        # Verify all entries were deleted
        assert count == 2
        assert APIResponseCache.objects.filter(user=user).count() == 0
