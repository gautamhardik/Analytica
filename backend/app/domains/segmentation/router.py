from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.segmentation.service import get_segmentation_data, _metadata
from app.domains.segmentation.schemas import SegmentationResponse
from app.domains.segmentation.repository import get_customer_segment, get_customer_categories

router = APIRouter(tags=["segmentation"])


@router.get("/segmentation/overview", response_model=SegmentationResponse)
async def segmentation_overview(session: AsyncSession = Depends(get_session)):
    return await get_segmentation_data(session)


@router.get("/segmentation/metadata")
async def segmentation_metadata():
    return _metadata


@router.get("/customers/{customer_id}/segment")
async def customer_segment(customer_id: str, session: AsyncSession = Depends(get_session)):
    segment = await get_customer_segment(session, customer_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Customer not found")
    categories = await get_customer_categories(session, customer_id)
    return {**segment, "purchased_categories": categories}
