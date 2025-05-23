from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class ClientResponses(BaseModel):
    websiteUrl: Optional[str] = None
    apiKey:     str
    email:      str 
    name:       Optional[str] = None
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
    planTitle: str
    subTitle: str
    callToAction: str

class DisplayServiceRecommendation(ServiceRecommendation):
    description: str
