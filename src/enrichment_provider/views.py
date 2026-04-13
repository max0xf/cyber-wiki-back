from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .registry import get_registry


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_enrichments(request):
    """
    Get all enrichments for a source URI.
    
    Query Parameters:
        source_uri: Universal source address (required)
        type: Filter by enrichment type (optional)
    
    Returns:
        Dictionary mapping enrichment types to lists of enrichments
    """
    source_uri = request.query_params.get('source_uri')
    enrichment_type = request.query_params.get('type')
    
    if not source_uri:
        return Response(
            {'error': 'source_uri parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    registry = get_registry()
    
    if enrichment_type:
        # Get enrichments of specific type
        enrichments = registry.get_enrichments_by_type(source_uri, request.user, enrichment_type)
        return Response({enrichment_type: enrichments})
    else:
        # Get all enrichments
        enrichments = registry.get_all_enrichments(source_uri, request.user)
        return Response(enrichments)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_enrichment_types(request):
    """
    Get list of available enrichment types.
    
    Returns:
        List of enrichment type strings
    """
    registry = get_registry()
    providers = registry.get_providers()
    types = [provider.get_enrichment_type() for provider in providers]
    return Response({'types': types})
