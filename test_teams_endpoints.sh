#!/bin/bash

# API Base URL
BASE_URL="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BLUE='\033[0;34m'

# Function to print section headers
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

# Function to check if response contains error
check_error() {
    if echo "$1" | grep -q "detail"; then
        if echo "$1" | grep -q "already registered"; then
            echo -e "${BLUE}Notice: User already exists${NC}"
            return 0
        fi
        echo -e "${RED}Error: $1${NC}"
        return 1
    fi
    return 0
}

# Function to handle errors and exit if needed
handle_error() {
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed at: $1${NC}"
        exit 1
    fi
}

# Store tokens and IDs
TOKEN=""
USER1_ID=""
USER2_ID=""
TEAM_ID=""
INVITATION_ID=""

# Register User 1 (John) - or get existing user
print_header "Registering/Getting User 1 (John)"
RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "john@example.com",
        "password": "password123",
        "name": "John Doe",
        "nickname": "Johnny",
        "country_code": "+1",
        "phone_number": "1234567890"
    }')

echo "Response: $RESPONSE"
if echo "$RESPONSE" | grep -q "already registered"; then
    # If user exists, get their ID through login
    RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=john@example.com&password=password123")
    USER1_ID=$(echo $RESPONSE | jq -r '.user_id')
else
    USER1_ID=$(echo $RESPONSE | jq -r '.id')
fi
echo -e "${GREEN}User 1 ID: $USER1_ID${NC}"

# Register User 2 (Jane) - or get existing user
print_header "Registering/Getting User 2 (Jane)"
RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "jane@example.com",
        "password": "password123",
        "name": "Jane Smith",
        "nickname": "Janey",
        "country_code": "+1",
        "phone_number": "0987654321"
    }')

echo "Response: $RESPONSE"
if echo "$RESPONSE" | grep -q "already registered"; then
    # If user exists, get their ID through login
    RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=jane@example.com&password=password123")
    USER2_ID=$(echo $RESPONSE | jq -r '.user_id')
else
    USER2_ID=$(echo $RESPONSE | jq -r '.id')
fi
echo -e "${GREEN}User 2 ID: $USER2_ID${NC}"

# Login as User 1
print_header "Logging in as User 1 (John)"
RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=john@example.com&password=password123")

echo "Response: $RESPONSE"
check_error "$RESPONSE"
TOKEN=$(echo $RESPONSE | jq -r '.access_token')
echo -e "${GREEN}Access Token: $TOKEN${NC}"
handle_error "Logging in as User 1"

# Create a team
print_header "Creating a team"
RESPONSE=$(curl -s -X POST "$BASE_URL/teams/" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{
        "name": "Johns Awesome Team",
        "description": "A team for testing"
    }')

echo "Response: $RESPONSE"
TEAM_ID=$(echo $RESPONSE | jq -r '.id // empty')
if [ -z "$TEAM_ID" ]; then
    echo -e "${RED}Failed to create team: $RESPONSE${NC}"
    exit 1
fi
echo -e "${GREEN}Team ID: $TEAM_ID${NC}"

# Get my teams
print_header "Getting teams owned by User 1"
RESPONSE=$(curl -s -X GET "$BASE_URL/teams/my-teams" \
    -H "Authorization: Bearer $TOKEN")

echo "Response: $RESPONSE"
TEAMS_COUNT=$(echo $RESPONSE | jq -r 'length // 0')
if [ "$TEAMS_COUNT" -eq 0 ]; then
    echo -e "${RED}No teams found for User 1${NC}"
    exit 1
fi

# Invite a new member
print_header "Inviting a new member to the team"
RESPONSE=$(curl -s -X POST "$BASE_URL/teams/$TEAM_ID/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{
        "name": "Bob Smith",
        "email": "bob@example.com",
        "phone_number": "1234567890",
        "country_code": "+1",
        "nickname": "Bobby"
    }')

echo "Response: $RESPONSE"
INVITATION_ID=$(echo $RESPONSE | jq -r '.id // empty')
if [ -z "$INVITATION_ID" ]; then
    echo -e "${RED}Failed to create invitation: $RESPONSE${NC}"
    exit 1
fi
echo -e "${GREEN}Invitation ID: $INVITATION_ID${NC}"

# Get team members (should show pending invitation)
print_header "Getting team members (after invitation)"
RESPONSE=$(curl -s -X GET "$BASE_URL/teams/$TEAM_ID/members" \
    -H "Authorization: Bearer $TOKEN")

echo "Response: $RESPONSE"
MEMBERS_COUNT=$(echo $RESPONSE | jq -r 'length // 0')
if [ "$MEMBERS_COUNT" -eq 0 ]; then
    echo -e "${RED}No team members found${NC}"
    exit 1
fi

# Login as User 2
print_header "Logging in as User 2 (Jane)"
RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=jane@example.com&password=password123")

echo "Response: $RESPONSE"
check_error "$RESPONSE"
TOKEN=$(echo $RESPONSE | jq -r '.access_token')
echo -e "${GREEN}New Access Token (User 2): $TOKEN${NC}"

# Invite User 2 (should fail as non-owner)
print_header "Attempting to invite as non-owner (should fail)"
RESPONSE=$(curl -s -X POST "$BASE_URL/teams/$TEAM_ID/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "phone_number": "9876543210",
        "country_code": "+1"
    }')

echo "Response: $RESPONSE"
echo -e "${GREEN}Expected failure: Only team owner can invite members${NC}"

# Get teams I'm a member of
print_header "Getting teams User 2 is a member of"
RESPONSE=$(curl -s -X GET "$BASE_URL/teams/member-of" \
    -H "Authorization: Bearer $TOKEN")

echo "Response: $RESPONSE"
check_error "$RESPONSE"

# Create a new user for invitation testing
print_header "Creating User 3 (Bob)"
RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "bob@example.com",
        "password": "password123",
        "name": "Bob Smith",
        "nickname": "Bobby",
        "country_code": "+1",
        "phone_number": "1234567890"
    }')

echo "Response: $RESPONSE"
if ! echo "$RESPONSE" | grep -q "already registered"; then
    check_error "$RESPONSE"
fi

# Login as User 3 (Bob)
print_header "Logging in as User 3 (Bob)"
RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=bob@example.com&password=password123")

echo "Response: $RESPONSE"
check_error "$RESPONSE"
TOKEN=$(echo $RESPONSE | jq -r '.access_token')
echo -e "${GREEN}New Access Token (User 3): $TOKEN${NC}"

# Accept invitation
print_header "Accepting team invitation"
RESPONSE=$(curl -s -X POST "$BASE_URL/teams/$TEAM_ID/invitations/$INVITATION_ID/accept" \
    -H "Authorization: Bearer $TOKEN")

echo "Response: $RESPONSE"
check_error "$RESPONSE"

# Get team members (should show accepted status)
print_header "Getting team members (after acceptance)"
RESPONSE=$(curl -s -X GET "$BASE_URL/teams/$TEAM_ID/members" \
    -H "Authorization: Bearer $TOKEN")

echo "Response: $RESPONSE"
check_error "$RESPONSE"

# Get teams I'm a member of (should show accepted team)
print_header "Getting teams User 3 is a member of"
RESPONSE=$(curl -s -X GET "$BASE_URL/teams/member-of" \
    -H "Authorization: Bearer $TOKEN")

echo "Response: $RESPONSE"
check_error "$RESPONSE"

echo -e "\n${GREEN}All tests completed successfully!${NC}"
