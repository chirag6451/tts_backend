from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from database import get_db
from models import User, Team, TeamMember, TeamRole, InvitationStatus
from schemas import TeamCreate, TeamResponse, TeamMemberCreate, TeamMemberResponse, TeamMemberInvite, InvitationResponse
from auth import get_current_user
from sqlalchemy import func
from enum import Enum
from pydantic import BaseModel

router = APIRouter(
    prefix="/teams",
    tags=["teams"]
)

def get_or_create_default_team(db: Session, current_user: User) -> Team:
    """Get the user's default team or create one if it doesn't exist"""
    # First try to find an existing team where the user is an owner
    default_team = (
        db.query(Team)
        .join(TeamMember)
        .filter(
            TeamMember.user_id == current_user.id,
            TeamMember.invitation_status == InvitationStatus.ACCEPTED.value
        )
        .order_by(Team.created_at)  # Get the oldest team (likely the default one)
        .first()
    )
    
    if not default_team:
        # Create a new default team for the user
        default_team = Team(
            name=f"{current_user.name}'s Team" if current_user.name else "My Team",
            description="Default team",
            owner_id=current_user.id
        )
        db.add(default_team)
        db.commit()
        db.refresh(default_team)
        
        # Add the owner as a team member
        db_team_member = TeamMember(
            team_id=default_team.id,
            user_id=current_user.id,
            role=TeamRole.OWNER.value,
            invitation_status=InvitationStatus.ACCEPTED.value,
            invited_by_id=current_user.id
        )
        db.add(db_team_member)
        db.commit()
    
    return default_team

def get_or_create_user_team(db: Session, current_user: User) -> Team:
    """Get existing team or create new one for the user"""
    team = (
        db.query(Team)
        .join(TeamMember)
        .filter(
            TeamMember.user_id == current_user.id,
            TeamMember.role == TeamRole.OWNER.value
        )
        .first()
    )
    
    if not team:
        # Create a new team for the user
        team = Team(
            name=f"{current_user.name}'s Team" if current_user.name else "My Team",
            owner_id=current_user.id
        )
        db.add(team)
        db.commit()
        db.refresh(team)
        
        # Add the owner as a team member
        db_team_member = TeamMember(
            team_id=team.id,
            user_id=current_user.id,
            role=TeamRole.OWNER.value,
            invitation_status=InvitationStatus.ACCEPTED.value,
            invited_by_id=current_user.id
        )
        db.add(db_team_member)
        db.commit()
    
    return team

class InvitationAction(str, Enum):
    ACCEPT = "accept"
    DECLINE = "decline"

class InvitationActionRequest(BaseModel):
    action: InvitationAction

@router.post("/invite", response_model=InvitationResponse)
def invite_team_members(
    invitation: TeamMemberInvite,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invite members to user's team."""
    invited_members = []
    errors = []

    # Get or create default team for the user
    default_team = get_or_create_default_team(db, current_user)

    for contact in invitation.contacts:
        try:
            # Determine which team to use
            team = None
            if contact.team_id:
                team = db.query(Team).filter(Team.id == contact.team_id).first()
                if not team:
                    errors.append(f"Team with id {contact.team_id} not found")
                    continue
                
                # Verify current user is team owner or member
                team_member = (
                    db.query(TeamMember)
                    .filter(
                        TeamMember.team_id == team.id,
                        TeamMember.user_id == current_user.id,
                        TeamMember.invitation_status == InvitationStatus.ACCEPTED.value
                    )
                    .first()
                )
                if not team_member:
                    errors.append(f"You don't have permission to invite members to team {contact.team_id}")
                    continue
            else:
                team = default_team

            # Find or create user placeholder
            user = None
            identifier = None

            if contact.email and contact.email.strip():
                user = db.query(User).filter(User.email == contact.email.strip()).first()
                identifier = contact.email
            elif contact.phone_number and contact.phone_number.strip():
                user = db.query(User).filter(User.phone_number == contact.phone_number.strip()).first()
                identifier = contact.phone_number
            else:
                errors.append("Either email or phone number must be provided")
                continue

            if user:
                # Check if user is already part of the team
                existing_member = (
                    db.query(TeamMember)
                    .filter(
                        TeamMember.team_id == team.id,
                        TeamMember.user_id == user.id,
                        TeamMember.invitation_status == InvitationStatus.ACCEPTED.value
                    )
                    .first()
                )
                
                if existing_member:
                    errors.append(f"Cannot invite {identifier} as they are already a member of this team")
                    continue

                # Check for pending invitation only for this specific team
                pending_invite = (
                    db.query(TeamMember)
                    .filter(
                        TeamMember.team_id == team.id,
                        TeamMember.user_id == user.id,
                        TeamMember.invitation_status == InvitationStatus.PENDING.value
                    )
                    .first()
                )
                
                if pending_invite:
                    errors.append(f"Cannot invite {identifier} as they already have a pending invitation to this team")
                    continue
            else:
                # Create placeholder user
                try:
                    # Check if phone number is already in use
                    if contact.phone_number and contact.phone_number.strip():
                        existing_user_with_phone = db.query(User).filter(User.phone_number == contact.phone_number.strip()).first()
                        if existing_user_with_phone:
                            errors.append(f"Phone number {contact.phone_number} is already registered with another user")
                            continue

                    user = User(
                        email=contact.email.strip() if contact.email and contact.email.strip() else None,
                        phone_number=contact.phone_number.strip() if contact.phone_number and contact.phone_number.strip() else None,
                        country_code=contact.country_code.strip() if contact.country_code and contact.country_code.strip() else None,
                        hashed_password="temporary"  # Will be set when user accepts invitation
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                except Exception as e:
                    errors.append(f"Failed to create user for {identifier}: {str(e)}")
                    db.rollback()
                    continue
            
            # Create new team member invitation
            db_team_member = TeamMember(
                team_id=team.id,
                user_id=user.id,
                role=TeamRole.MEMBER.value,
                invitation_status=InvitationStatus.PENDING.value,
                invited_by_id=current_user.id
            )
            db.add(db_team_member)
            db.commit()
            db.refresh(db_team_member)
            
            invited_members.append(db_team_member)

        except Exception as e:
            errors.append(f"Failed to process invitation for {identifier}: {str(e)}")
            db.rollback()
            continue
    
    if not invited_members and errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Failed to invite any members", "errors": errors}
        )
    
    return {
        "members": invited_members,
        "errors": errors if errors else None
    }

@router.post("/{team_id}/invitations/{invitation_id}/respond", response_model=TeamMemberResponse)
def respond_to_invitation(
    team_id: int,
    invitation_id: int,
    action: InvitationActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Respond to a team invitation"""
    # Find the invitation
    invitation = (
        db.query(TeamMember)
        .filter(
            TeamMember.id == invitation_id,
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.invitation_status == InvitationStatus.PENDING.value
        )
        .first()
    )
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or already processed"
        )
    
    # Update invitation status based on action
    if action.action == InvitationAction.ACCEPT:
        invitation.invitation_status = InvitationStatus.ACCEPTED.value
    else:
        invitation.invitation_status = InvitationStatus.DECLINED.value
    
    db.commit()
    db.refresh(invitation)
    
    return invitation

@router.post("/invitations/accept", response_model=TeamMemberResponse)
def accept_invitation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept pending team invitation for the current user"""
    # Find pending invitation for the user
    pending_invitation = (
        db.query(TeamMember)
        .filter(
            TeamMember.user_id == current_user.id,
            TeamMember.invitation_status == InvitationStatus.PENDING.value
        )
        .first()
    )
    
    if not pending_invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending invitation found"
        )
    
    # Update invitation status
    pending_invitation.invitation_status = InvitationStatus.ACCEPTED.value
    db.commit()
    db.refresh(pending_invitation)
    
    return pending_invitation

@router.post("/invitations/decline", response_model=TeamMemberResponse)
def decline_invitation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Decline pending team invitation for the current user"""
    # Find pending invitation for the user
    pending_invitation = (
        db.query(TeamMember)
        .filter(
            TeamMember.user_id == current_user.id,
            TeamMember.invitation_status == InvitationStatus.PENDING.value
        )
        .first()
    )
    
    if not pending_invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending invitation found"
        )
    
    # Update invitation status
    pending_invitation.invitation_status = InvitationStatus.DECLINED.value
    db.commit()
    db.refresh(pending_invitation)
    
    return pending_invitation

@router.get("/my", response_model=TeamResponse)
def get_my_team(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's team"""
    team = get_or_create_user_team(db, current_user)
    return team

@router.get("/invitations", response_model=List[TeamMemberResponse])
def get_my_invitations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all pending invitations for the current user"""
    return (
        db.query(TeamMember)
        .filter(
            TeamMember.user_id == current_user.id,
            TeamMember.invitation_status == InvitationStatus.PENDING.value
        )
        .all()
    )
