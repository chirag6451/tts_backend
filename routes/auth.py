from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional

from ..database import SessionLocal
from ..models import User, Team, TeamMember, InvitationStatus
from ..schemas import UserCreate, RegistrationResponse, Token
from ..auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
import logging
from sqlalchemy import text

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register", response_model=RegistrationResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        logger.info("=== Starting Registration Process ===")
        logger.info(f"Registration request for email: {user.email}, phone: {user.phone_number}")
        
        # Check if user exists by email or phone
        existing_user = None
        
        # First check by email
        if user.email:
            logger.info(f"Checking for existing user by email: {user.email}")
            email_query = db.query(User).filter(User.email == user.email)
            logger.info(f"Email query SQL: {str(email_query)}")
            existing_user = email_query.first()
            if existing_user:
                logger.info(f"Found user by email - ID: {existing_user.id}")
                # Log all user details
                logger.info(f"User details: email={existing_user.email}, phone={existing_user.phone_number}, name={existing_user.name}")
        
        # Then check by phone if no user found
        if not existing_user and user.phone_number:
            logger.info(f"Checking for existing user by phone: {user.phone_number}")
            phone_query = db.query(User).filter(User.phone_number == user.phone_number)
            logger.info(f"Phone query SQL: {str(phone_query)}")
            existing_user = phone_query.first()
            if existing_user:
                logger.info(f"Found user by phone - ID: {existing_user.id}")
                logger.info(f"User details: email={existing_user.email}, phone={existing_user.phone_number}, name={existing_user.name}")

        if existing_user:
            logger.info("=== Processing Existing User ===")
            logger.info(f"Found existing user with ID: {existing_user.id}")
            
            # Direct SQL query to check team memberships
            membership_sql = text(
                "SELECT * FROM team_members WHERE user_id = :user_id"
            )
            result = db.execute(membership_sql, {"user_id": existing_user.id})
            raw_memberships = result.fetchall()
            logger.info(f"Raw SQL membership results: {raw_memberships}")
            
            # Check team memberships using SQLAlchemy
            logger.info(f"Checking team memberships for user: {existing_user.id}")
            team_query = db.query(TeamMember).filter(TeamMember.user_id == existing_user.id)
            logger.info(f"Team membership query SQL: {str(team_query)}")
            team_memberships = team_query.all()
            
            logger.info(f"Found {len(team_memberships)} team memberships")
            
            # Log each membership in detail
            for member in team_memberships:
                logger.info(f"Team Membership Details:")
                logger.info(f"  - ID: {member.id}")
                logger.info(f"  - Team ID: {member.team_id}")
                logger.info(f"  - Status: {member.invitation_status}")
                logger.info(f"  - Status Type: {type(member.invitation_status)}")
                logger.info(f"  - Status == 'pending': {member.invitation_status == 'pending'}")
                logger.info(f"  - Role: {member.role}")
            
            # Check for non-pending invitations
            has_non_pending = any(
                member.invitation_status != "pending"  
                for member in team_memberships
            )
            logger.info(f"Has non-pending invitations: {has_non_pending}")
            
            if not team_memberships:
                logger.info("No team memberships found - blocking registration")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            if has_non_pending:
                logger.info("Found non-pending invitations - blocking registration")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            logger.info("All invitations are pending - proceeding with registration")
            # Update user details
            logger.info("Updating user details")
            existing_user.email = user.email
            existing_user.hashed_password = get_password_hash(user.password)
            existing_user.name = user.name
            existing_user.nickname = user.nickname
            existing_user.country_code = user.country_code
            existing_user.phone_number = user.phone_number
            db.commit()
            db.refresh(existing_user)
            db_user = existing_user
            logger.info(f"Successfully updated user details for ID: {db_user.id}")
        else:
            logger.info("=== Creating New User ===")
            # Create new user
            hashed_password = get_password_hash(user.password)
            db_user = User(
                email=user.email,
                hashed_password=hashed_password,
                name=user.name,
                nickname=user.nickname,
                country_code=user.country_code,
                phone_number=user.phone_number
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            logger.info(f"Created new user with ID: {db_user.id}")

        # Find pending invitations
        logger.info("=== Checking Pending Invitations ===")
        logger.info(f"Finding pending invitations for user: {db_user.id}")
        pending_invitations = []
        invitations_query = (
            db.query(
                TeamMember,
                Team.name.label('team_name'),
                User.name.label('inviter_name')
            )
            .join(Team, TeamMember.team_id == Team.id)
            .outerjoin(User, TeamMember.invited_by_id == User.id)
            .filter(
                TeamMember.invitation_status == InvitationStatus.PENDING.value,
                TeamMember.user_id == db_user.id
            )
        )
        logger.info(f"Pending invitations query SQL: {str(invitations_query)}")
        
        for invite, team_name, inviter_name in invitations_query.all():
            logger.info(f"Found pending invitation - ID: {invite.id}, Team: {team_name}")
            pending_invitations.append({
                "id": invite.id,
                "team_id": invite.team_id,
                "team_name": team_name,
                "invited_by_name": inviter_name,
                "invited_at": invite.invited_at
            })

        logger.info(f"Total pending invitations found: {len(pending_invitations)}")

        # Prepare response
        response_data = {
            "id": db_user.id,
            "email": db_user.email,
            "name": db_user.name,
            "nickname": db_user.nickname,
            "country_code": db_user.country_code,
            "phone_number": db_user.phone_number,
            "created_at": db_user.created_at,
            "pending_invitations": pending_invitations
        }
        
        logger.info("=== Registration Successful ===")
        return response_data
        
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}", exc_info=True)
        raise

@router.post("/login", response_model=Token)
async def login(email: str, password: str, db: Session = Depends(get_db)):
    # Find user by email
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id
    }
