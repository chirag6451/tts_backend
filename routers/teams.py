from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from database import get_db
from models import User, Team, TeamMember, TeamRole, InvitationStatus
from schemas import TeamCreate, TeamResponse, TeamMemberCreate, TeamMemberResponse, TeamMemberInvite, InvitationResponse
from auth import get_current_user
from sqlalchemy import func

router = APIRouter(
    prefix="/teams",
    tags=["teams"]
)

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

@router.post("/invite", response_model=InvitationResponse)
def invite_team_members(
    invitation: TeamMemberInvite,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invite members to user's team. Creates team if doesn't exist."""
    team = get_or_create_user_team(db, current_user)
    
    invited_members = []
    errors = []

    for contact in invitation.contacts:
        try:
            # Validate that either email or phone is provided
            if not contact.email and not (contact.phone_number and contact.country_code):
                errors.append("Either email or phone number with country code must be provided")
                continue
                
            # Find or create user placeholder
            user = None
            if contact.email:
                user = db.query(User).filter(User.email == contact.email).first()
            elif contact.phone_number and contact.country_code:
                user = db.query(User).filter(
                    User.phone_number == contact.phone_number,
                    User.country_code == contact.country_code
                ).first()
            
            identifier = contact.email or f"{contact.country_code}{contact.phone_number}"
            
            if user:
                # Check if user is already part of the current team
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
                    errors.append(f"Cannot invite {identifier} as they are already a member of your team")
                    continue

                # Check for pending invitation to this team
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
                    errors.append(f"Cannot invite {identifier} as they already have a pending invitation to your team")
                    continue

            else:
                # Create placeholder user
                try:
                    user = User(
                        email=contact.email,
                        phone_number=contact.phone_number,
                        country_code=contact.country_code,
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
