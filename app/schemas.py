from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class ClientResponses(BaseModel):
    websiteUrl: Optional[str] = None
    agencyId:  Optional[str] = None
    apiKey:    Optional[str] = None
    email:     Optional[str] = None
    name:      Optional[str] = None
    # __root__ is removed. Extra fields will be caught by model_extra.

    class Config:
        extra = 'allow'  # Allow extra fields and store them

class ServiceRecommendation(BaseModel):
    id: int
    serviceId: str
    reason:    str

class WebsiteAnalysis(BaseModel):
    companyName:        str
    strengths:          List[str]
    weaknesses:         List[str]
    recommendations:    List[str]
    overallImpression:  str

class AIResponse(BaseModel):
    recommendations: List[ServiceRecommendation]
    executiveSummary: str

class DisplayServiceRecommendation(ServiceRecommendation):
    description: str
