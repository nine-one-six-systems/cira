"""Version history and comparison API routes."""

from flask import request

from app import db
from app.api import api_bp
from app.api.routes.companies import make_error_response, make_success_response
from app.models.company import Company, Analysis, TokenUsage
from app.schemas import (
    VersionItem,
    CompareVersionsResponse,
    VersionChange,
    VersionChanges,
    ApiResponse,
)


@api_bp.route('/companies/<company_id>/versions', methods=['GET'])
def list_versions(company_id: str):
    """Get analysis version history."""
    company = db.session.get(Company, company_id)
    if not company:
        return make_error_response('NOT_FOUND', 'Company not found', status=404)

    # Get all analyses for the company
    analyses = (
        Analysis.query
        .filter_by(company_id=company_id)
        .order_by(Analysis.version_number.desc())
        .all()
    )

    # Build version items
    items = []
    for a in analyses:
        # Calculate tokens used for this version
        tokens_used = 0
        if a.token_breakdown:
            tokens_used = sum(a.token_breakdown.values())

        item = VersionItem(
            analysisId=a.id,
            versionNumber=a.version_number,
            createdAt=a.created_at,
            tokensUsed=tokens_used
        )
        items.append(item.model_dump(by_alias=True, mode='json'))

    response = ApiResponse[list](data=items)
    return response.model_dump(by_alias=True)


@api_bp.route('/companies/<company_id>/compare', methods=['GET'])
def compare_versions(company_id: str):
    """Compare two analysis versions."""
    company = db.session.get(Company, company_id)
    if not company:
        return make_error_response('NOT_FOUND', 'Company not found', status=404)

    # Get version parameters
    version1 = request.args.get('version1', type=int)
    version2 = request.args.get('version2', type=int)

    if not version1 or not version2:
        return make_error_response(
            'VALIDATION_ERROR',
            'Both version1 and version2 query parameters are required'
        )

    if version1 <= 0 or version2 <= 0:
        return make_error_response(
            'VALIDATION_ERROR',
            'Version numbers must be positive integers'
        )

    # Get both analyses
    analysis1 = (
        Analysis.query
        .filter_by(company_id=company_id, version_number=version1)
        .first()
    )
    analysis2 = (
        Analysis.query
        .filter_by(company_id=company_id, version_number=version2)
        .first()
    )

    if not analysis1:
        return make_error_response(
            'NOT_FOUND',
            f'Version {version1} not found',
            status=404
        )

    if not analysis2:
        return make_error_response(
            'NOT_FOUND',
            f'Version {version2} not found',
            status=404
        )

    # Compare analyses
    team_changes = []
    product_changes = []
    content_changes = []

    # Compare full_analysis if present
    data1 = analysis1.full_analysis or {}
    data2 = analysis2.full_analysis or {}

    # Compare team section
    team1 = data1.get('team', {})
    team2 = data2.get('team', {})
    team_changes.extend(compare_dicts(team1, team2, 'team'))

    # Compare products section
    products1 = data1.get('products', [])
    products2 = data2.get('products', [])
    product_changes.extend(compare_values(products1, products2, 'products'))

    # Compare executive summary
    if analysis1.executive_summary != analysis2.executive_summary:
        content_changes.append(VersionChange(
            field='executiveSummary',
            previousValue=analysis1.executive_summary[:100] if analysis1.executive_summary else None,
            currentValue=analysis2.executive_summary[:100] if analysis2.executive_summary else None,
            changeType='modified' if analysis1.executive_summary and analysis2.executive_summary else (
                'added' if analysis2.executive_summary else 'removed'
            )
        ))

    changes = VersionChanges(
        team=team_changes,
        products=product_changes,
        content=content_changes
    )

    significant_changes = (
        len(team_changes) > 0 or
        len(product_changes) > 0 or
        len(content_changes) > 0
    )

    response = CompareVersionsResponse(
        companyId=company_id,
        previousVersion=min(version1, version2),
        currentVersion=max(version1, version2),
        changes=changes,
        significantChanges=significant_changes
    )

    return make_success_response(response.model_dump(by_alias=True, mode='json'))


def compare_values(val1, val2, section: str) -> list[VersionChange]:
    """Compare two values (dicts or lists) and return a list of changes."""
    changes = []

    # Handle case when both are dicts
    if isinstance(val1, dict) and isinstance(val2, dict):
        all_keys = set(val1.keys()) | set(val2.keys())
        for key in all_keys:
            v1 = val1.get(key)
            v2 = val2.get(key)
            if v1 != v2:
                if v1 is None:
                    change_type = 'added'
                elif v2 is None:
                    change_type = 'removed'
                else:
                    change_type = 'modified'
                changes.append(VersionChange(
                    field=key,
                    previousValue=v1,
                    currentValue=v2,
                    changeType=change_type
                ))
    # Handle case when both are lists
    elif isinstance(val1, list) and isinstance(val2, list):
        if val1 != val2:
            # Find added items
            for item in val2:
                if item not in val1:
                    changes.append(VersionChange(
                        field=str(item),
                        previousValue=None,
                        currentValue=item,
                        changeType='added'
                    ))
            # Find removed items
            for item in val1:
                if item not in val2:
                    changes.append(VersionChange(
                        field=str(item),
                        previousValue=item,
                        currentValue=None,
                        changeType='removed'
                    ))
    # Handle case when types differ or one is not present
    elif val1 != val2:
        if val1 is None or val1 == []:
            change_type = 'added'
        elif val2 is None or val2 == []:
            change_type = 'removed'
        else:
            change_type = 'modified'
        changes.append(VersionChange(
            field=section,
            previousValue=val1,
            currentValue=val2,
            changeType=change_type
        ))

    return changes


def compare_dicts(dict1: dict, dict2: dict, section: str) -> list[VersionChange]:
    """Compare two dictionaries and return a list of changes."""
    return compare_values(dict1 or {}, dict2 or {}, section)
