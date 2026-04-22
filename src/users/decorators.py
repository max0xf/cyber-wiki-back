"""
Decorators for API response caching.
"""
import functools
import logging
from typing import Callable, Optional
from django.http import JsonResponse
from rest_framework.response import Response

from .cache import get_cache

logger = logging.getLogger(__name__)


def cached_api_response(
    provider_type_param: str = 'provider_type',
    provider_id_param: str = 'provider_id',
    endpoint_func: Optional[Callable] = None
):
    """
    Decorator to cache API responses.
    
    Automatically caches successful API responses (200-299 status codes) and
    returns cached responses when available and not expired.
    
    Usage:
        # Simple usage (uses request path as endpoint)
        @cached_api_response()
        def my_view(request):
            return JsonResponse({'data': 'value'})
        
        # Custom endpoint extraction
        @cached_api_response(
            endpoint_func=lambda view, **kwargs: f"/repos/{kwargs['repo_slug']}"
        )
        def repo_view(request, repo_slug):
            return JsonResponse({'repo': repo_slug})
        
        # DRF ViewSet action
        @cached_api_response(
            provider_type_param='provider',
            endpoint_func=lambda view, **kwargs: f"/repositories/{kwargs.get('pk', '')}"
        )
        @action(detail=True, methods=['get'])
        def tree(self, request, pk=None):
            return Response({'tree': 'data'})
    
    Args:
        provider_type_param: Name of parameter containing provider type (default: 'provider_type')
        provider_id_param: Name of parameter containing provider ID (default: 'provider_id')
        endpoint_func: Optional function to extract endpoint path from view kwargs.
                      Signature: (view_func, **kwargs) -> str
                      If None, uses request.path
    
    Cache Key Components:
        - user: Authenticated user (cache is per-user)
        - provider_type: Git provider type (github, bitbucket_server, etc.)
        - provider_id: Provider instance ID (e.g., github.com, git.example.com)
        - endpoint: API endpoint path
        - params: Query parameters + URL kwargs (excluding provider params)
        - method: HTTP method (GET, POST, etc.)
    
    Cache Headers:
        - X-Cache: HIT (from cache) or MISS (fresh from API)
        - X-Cache-Date: ISO timestamp when response was cached (only on HIT)
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request_or_self, *args, **kwargs):
            # Handle both function-based views and class-based views (DRF ViewSets)
            if hasattr(request_or_self, 'request'):
                # DRF ViewSet - first arg is self
                request = request_or_self.request
                view_self = request_or_self
            else:
                # Function-based view - first arg is request
                request = request_or_self
                view_self = None
            
            user = request.user
            if not user.is_authenticated:
                # No caching for unauthenticated users
                if view_self:
                    return view_func(view_self, *args, **kwargs)
                return view_func(request, *args, **kwargs)
            
            cache = get_cache(user)
            
            # Only cache if enabled for this user
            if not cache.is_enabled():
                if view_self:
                    return view_func(view_self, *args, **kwargs)
                return view_func(request, *args, **kwargs)
            
            # Extract cache key components
            provider_type = kwargs.get(provider_type_param, 'unknown')
            provider_id = kwargs.get(provider_id_param, 'unknown')
            
            # Build endpoint path
            if endpoint_func:
                endpoint = endpoint_func(view_func, **kwargs)
            else:
                endpoint = request.path
            
            # Build params from query string and kwargs
            params = dict(request.GET.items())
            # Add URL kwargs (excluding provider params)
            params.update({
                k: str(v) for k, v in kwargs.items()
                if k not in [provider_type_param, provider_id_param]
            })
            
            method = request.method
            
            # Try to get from cache
            cached = cache.get(provider_type, provider_id, endpoint, params, method)
            if cached:
                logger.info(f'Cache HIT for {endpoint} (user: {user.username})')
                headers = {
                    'X-Cache': 'HIT',
                    'X-Cache-Date': cached.get('cached_at', '')
                }
                
                # Return appropriate response type
                if view_self:
                    # DRF Response
                    response = Response(
                        cached['data'],
                        status=cached['status_code']
                    )
                    for key, value in headers.items():
                        response[key] = value
                    return response
                else:
                    # Django JsonResponse
                    return JsonResponse(
                        cached['data'],
                        status=cached['status_code'],
                        headers=headers
                    )
            
            # Call original view
            if view_self:
                response = view_func(view_self, *args, **kwargs)
            else:
                response = view_func(request, *args, **kwargs)
            
            # Cache successful responses (200-299)
            if 200 <= response.status_code < 300:
                try:
                    # Extract data from response
                    if isinstance(response, Response):
                        # DRF Response
                        response_data = response.data
                    elif isinstance(response, JsonResponse):
                        # Django JsonResponse
                        import json
                        response_data = json.loads(response.content.decode('utf-8'))
                    else:
                        # Unknown response type, skip caching
                        logger.warning(f'Cannot cache response type: {type(response)}')
                        return response
                    
                    cache.set(
                        provider_type,
                        provider_id,
                        endpoint,
                        params,
                        response_data,
                        response.status_code,
                        method
                    )
                    
                    # Add cache header
                    response['X-Cache'] = 'MISS'
                    logger.info(f'Cache MISS for {endpoint} (user: {user.username}) - cached for future')
                    
                except Exception as e:
                    logger.error(f'Failed to cache response: {e}')
            
            return response
        
        return wrapper
    return decorator
