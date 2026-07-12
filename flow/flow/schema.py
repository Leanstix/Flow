import re
from collections import OrderedDict

from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema


ERROR_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    description='Validation or request error. Field-specific errors may replace the generic error key.',
    properties={
        'error': openapi.Schema(type=openapi.TYPE_STRING, example='A human-readable error message.'),
        'detail': openapi.Schema(type=openapi.TYPE_STRING, example='Authentication credentials were not provided.'),
    },
)

MESSAGE_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'message': openapi.Schema(type=openapi.TYPE_STRING, example='Operation completed successfully.'),
    },
)

COUNT_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'updated_count': openapi.Schema(type=openapi.TYPE_INTEGER, example=3),
    },
)

TOKEN_PAIR_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'access': openapi.Schema(type=openapi.TYPE_STRING, description='Short-lived JWT access token.'),
        'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Long-lived JWT refresh token.'),
        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, example=42),
        'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=42),
        'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, example='student@example.com'),
        'user_name': openapi.Schema(type=openapi.TYPE_STRING, example='leanstix'),
        'first_name': openapi.Schema(type=openapi.TYPE_STRING, example='Olamilekan'),
        'last_name': openapi.Schema(type=openapi.TYPE_STRING, example='Aleshinloye'),
        'profile_picture': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, x_nullable=True),
    },
)


def obj(properties, required=None, example=None, description=None):
    kwargs = {
        'type': openapi.TYPE_OBJECT,
        'properties': properties,
    }
    if required:
        kwargs['required'] = required
    if example is not None:
        kwargs['example'] = example
    if description:
        kwargs['description'] = description
    return openapi.Schema(**kwargs)


def string(description='', example=None, enum=None, fmt=None):
    kwargs = {'type': openapi.TYPE_STRING}
    if description:
        kwargs['description'] = description
    if example is not None:
        kwargs['example'] = example
    if enum:
        kwargs['enum'] = enum
    if fmt:
        kwargs['format'] = fmt
    return openapi.Schema(**kwargs)


def integer(description='', example=None):
    kwargs = {'type': openapi.TYPE_INTEGER}
    if description:
        kwargs['description'] = description
    if example is not None:
        kwargs['example'] = example
    return openapi.Schema(**kwargs)


def array(items, description=''):
    return openapi.Schema(type=openapi.TYPE_ARRAY, items=items, description=description)


def response(description, schema=None):
    return openapi.Response(description=description, schema=schema)


def query(name, description, type_=openapi.TYPE_STRING, required=False, enum=None, default=None):
    kwargs = {
        'name': name,
        'in_': openapi.IN_QUERY,
        'description': description,
        'type': type_,
        'required': required,
    }
    if enum:
        kwargs['enum'] = enum
    if default is not None:
        kwargs['default'] = default
    return openapi.Parameter(**kwargs)


def markdown(purpose, authentication, behaviour, request_example=None, response_example=None, errors=None, notes=None):
    sections = [
        purpose.strip(),
        f'**Authentication:** {authentication}',
        '**Behaviour and side effects**\n' + '\n'.join(f'- {item}' for item in behaviour),
    ]
    if request_example:
        sections.append('**Request example**\n```json\n' + request_example.strip() + '\n```')
    if response_example:
        sections.append('**Successful response example**\n```json\n' + response_example.strip() + '\n```')
    if errors:
        sections.append('**Expected errors**\n' + '\n'.join(f'- {item}' for item in errors))
    if notes:
        sections.append('**Integration notes**\n' + '\n'.join(f'- {item}' for item in notes))
    return '\n\n'.join(sections)


PAGINATION_PARAMETERS = [
    query('page', 'One-based page number.', openapi.TYPE_INTEGER, default=1),
    query('limit', 'Maximum records per page when the endpoint supports configurable pagination.', openapi.TYPE_INTEGER),
]


RESOURCE_DOCS = {
    'AdvertisementViewSet': {
        'tag': 'Marketplace',
        'singular': 'marketplace listing',
        'plural': 'marketplace listings',
        'description': 'Student marketplace adverts with images, pricing, condition, location, saves, moderation and seller messaging.',
        'identifier': 'numeric listing ID',
        'list_notes': [
            'Returns active and reserved listings by default; archived listings are excluded.',
            'Supports text, category, condition, status, seller, price and ordering filters.',
            'The response includes viewer-specific fields such as is_saved and is_owner.',
        ],
        'create_notes': [
            'The authenticated user becomes the seller automatically.',
            'Accepts JSON or multipart/form-data when listing images are included.',
            'Server-side validation controls category, condition, price and image count.',
        ],
        'retrieve_notes': [
            'Opening another seller’s listing increments the view counter.',
            'Archived listings are not returned through the normal detail route.',
        ],
        'update_notes': [
            'Only the seller or a staff user may update the listing.',
            'PATCH updates only supplied fields; PUT expects a complete writable representation.',
        ],
        'destroy_notes': [
            'Delete is a soft archive operation; the database record is retained.',
            'Only the seller or a staff user may archive the listing.',
        ],
        'list_parameters': [
            query('q', 'Case-insensitive search across title, description, location and seller username.'),
            query('category', 'Filter by listing category.', enum=['books', 'electronics', 'fashion', 'services', 'accommodation', 'food', 'other']),
            query('condition', 'Filter by item condition.', enum=['new', 'like_new', 'used', 'not_applicable']),
            query('status', 'Filter by listing status.', enum=['active', 'reserved', 'sold', 'archived']),
            query('seller', 'Filter by numeric seller user ID.', openapi.TYPE_INTEGER),
            query('min_price', 'Minimum price, inclusive.'),
            query('max_price', 'Maximum price, inclusive.'),
            query('ordering', 'Sort field. Prefix with - for descending order.', enum=['created_at', '-created_at', 'price', '-price', 'views_count', '-views_count', 'saved_count', '-saved_count'], default='-created_at'),
            *PAGINATION_PARAMETERS,
        ],
    },
    'CommunityViewSet': {
        'tag': 'Communities',
        'singular': 'community',
        'plural': 'communities',
        'description': 'Course, project, club and interest communities with public/private membership workflows.',
        'identifier': 'community slug',
        'list_notes': [
            'Returns active communities with member, post and resource counts.',
            'Viewer membership status and role are included when available.',
        ],
        'create_notes': [
            'The authenticated user becomes the owner.',
            'An active owner membership is created in the same transaction.',
        ],
        'retrieve_notes': ['Returns one active community by slug.'],
        'update_notes': ['Only the owner or authorized staff can update ownership-controlled fields.'],
        'destroy_notes': ['Delete deactivates the community instead of removing historical records.'],
        'list_parameters': [
            query('q', 'Search community name, description and course code.'),
            query('category', 'Filter by category.', enum=['course', 'interest', 'project', 'club']),
            query('course_code', 'Exact case-insensitive course-code filter.'),
            query('mine', 'Use true to return communities where the current user is an active member.', openapi.TYPE_BOOLEAN),
            *PAGINATION_PARAMETERS,
        ],
    },
    'CommunityPostViewSet': {
        'tag': 'Community posts',
        'singular': 'community post',
        'plural': 'community posts',
        'description': 'Posts created inside Flow communities.',
        'identifier': 'numeric community-post ID',
        'list_notes': [
            'Public-community posts are visible to authenticated users.',
            'Private-community posts are visible only to active members.',
        ],
        'create_notes': ['The author must be an active member of the target community.'],
        'retrieve_notes': ['Visibility follows the community’s membership rules.'],
        'update_notes': ['Only the author or a community moderator may modify content.'],
        'destroy_notes': ['Only the author or a community moderator may delete content.'],
        'list_parameters': [
            query('community', 'Filter by community slug.'),
            *PAGINATION_PARAMETERS,
        ],
    },
    'CommunityResourceViewSet': {
        'tag': 'Community resources',
        'singular': 'community resource',
        'plural': 'community resources',
        'description': 'Links and learning resources shared inside communities.',
        'identifier': 'numeric resource ID',
        'list_notes': ['Only resources from communities where the viewer is an active member are returned.'],
        'create_notes': ['The uploader must be an active member of the target community.'],
        'retrieve_notes': ['Membership is required.'],
        'update_notes': ['Only the uploader or a moderator may update the resource.'],
        'destroy_notes': ['Only the uploader or a moderator may delete the resource.'],
        'list_parameters': [
            query('community', 'Filter by community slug.'),
            *PAGINATION_PARAMETERS,
        ],
    },
    'ConversationViewSet': {
        'tag': 'Messaging',
        'singular': 'conversation',
        'plural': 'conversations',
        'description': 'Private direct and group conversations belonging to the authenticated participant.',
        'identifier': 'numeric conversation ID',
        'list_notes': [
            'Only conversations containing the authenticated user are returned.',
            'Each item includes participants, display name, last message and unread count.',
        ],
        'create_notes': [
            'Send a non-empty participants array; the current user is inserted automatically.',
            'An existing exact two-person conversation is reused instead of duplicated.',
            'Group conversations are created when more than two unique participants are supplied.',
        ],
        'retrieve_notes': ['Participant isolation is enforced by the queryset.'],
        'update_notes': ['Conversation participants are read-only in the current serializer.'],
        'destroy_notes': ['Deleting a conversation removes its persisted message history for all participants.'],
        'list_parameters': PAGINATION_PARAMETERS,
    },
    'MessageViewSet': {
        'tag': 'Messaging',
        'singular': 'message',
        'plural': 'messages',
        'description': 'Conversation messages with replies, attachments and delivery/read receipts.',
        'identifier': 'numeric message ID',
        'list_notes': ['Only messages from conversations containing the authenticated user are visible.'],
        'create_notes': [
            'Use conversation to identify the destination.',
            'Text, typed attachments or both may be supplied.',
            'A receipt is created for each other participant and websocket events are broadcast after commit.',
        ],
        'retrieve_notes': ['Participants can retrieve message content and receipt state.'],
        'update_notes': [
            'Only the sender can edit a message.',
            'Deleted messages cannot be edited.',
            'The edited_at timestamp is updated and a realtime message.updated event is emitted.',
        ],
        'destroy_notes': [
            'Only the sender can delete a message.',
            'Deletion is soft: content and attachments are hidden while a deleted marker remains.',
        ],
        'list_parameters': PAGINATION_PARAMETERS,
    },
    'NotificationViewSet': {
        'tag': 'Notifications',
        'singular': 'notification',
        'plural': 'notifications',
        'description': 'Private notifications for messages, likes, comments, mentions, reposts, friendships and system events.',
        'identifier': 'numeric notification ID',
        'list_notes': ['Only notifications whose recipient is the authenticated user are returned.'],
        'retrieve_notes': ['Cross-user notification access is blocked by the recipient-filtered queryset.'],
        'list_parameters': PAGINATION_PARAMETERS,
    },
}


STANDARD_ACTION_LABELS = {
    'list': ('List', 'Returns a collection of'),
    'create': ('Create', 'Creates a new'),
    'retrieve': ('Retrieve', 'Returns one'),
    'update': ('Replace', 'Replaces the writable fields of one'),
    'partial_update': ('Update', 'Updates selected writable fields of one'),
    'destroy': ('Delete', 'Deletes or archives one'),
}


def standard_resource_doc(view_name, action):
    resource = RESOURCE_DOCS.get(view_name)
    labels = STANDARD_ACTION_LABELS.get(action)
    if not resource or not labels:
        return None

    verb, sentence = labels
    plural = resource['plural']
    singular = resource['singular']
    identifier = resource['identifier']
    noun = plural if action == 'list' else singular
    notes_key = {
        'list': 'list_notes',
        'create': 'create_notes',
        'retrieve': 'retrieve_notes',
        'update': 'update_notes',
        'partial_update': 'update_notes',
        'destroy': 'destroy_notes',
    }[action]
    notes = resource.get(notes_key, [])
    behaviour = [resource['description'], *notes]
    if action in {'retrieve', 'update', 'partial_update', 'destroy'}:
        behaviour.insert(1, f'The resource is selected by {identifier}.')

    success = {
        'list': f'A paginated or plain collection of {plural}, depending on configured pagination.',
        'create': f'The created {singular}.',
        'retrieve': f'The requested {singular}.',
        'update': f'The replaced {singular}.',
        'partial_update': f'The updated {singular}.',
        'destroy': 'HTTP 204 with no response body.',
    }[action]

    errors = ['400 when submitted fields or filters are invalid.']
    if action != 'list':
        errors.append('404 when the resource does not exist or is outside the authenticated user’s permitted queryset.')
    if action in {'create', 'update', 'partial_update', 'destroy'}:
        errors.append('403 when the authenticated user does not have permission to perform the write.')

    return {
        'tag': resource['tag'],
        'summary': f'{verb} {noun}',
        'description': markdown(
            f'{sentence} {noun}.',
            'Required. Send `Authorization: Bearer <access-token>`.',
            behaviour,
            response_example=success,
            errors=errors,
        ),
        'parameters': resource.get('list_parameters', []) if action == 'list' else [],
    }


PUBLIC = 'Not required.'
AUTH = 'Required. Send `Authorization: Bearer <access-token>`.'


CUSTOM_DOCS = {
    ('LoginView', 'post'): {
        'tag': 'Authentication',
        'summary': 'Sign in with email and password',
        'public': True,
        'request_schema': obj(
            {
                'email': string('Registered email address.', 'student@example.com', fmt=openapi.FORMAT_EMAIL),
                'password': string('Account password.', 'strong-password'),
            },
            required=['email', 'password'],
        ),
        'responses': {
            200: response('JWT tokens and the authenticated user profile.', TOKEN_PAIR_SCHEMA),
        },
        'description': markdown(
            'Authenticates an activated Flow account and issues JWT credentials.',
            PUBLIC,
            [
                'Email and password are validated by the configured email authentication backend.',
                'The access token is short-lived and must be sent as a Bearer token to protected endpoints.',
                'The refresh token can be exchanged for a new access token.',
            ],
            '{\n  "email": "student@example.com",\n  "password": "strong-password"\n}',
            '{\n  "access": "eyJ...",\n  "refresh": "eyJ...",\n  "user_id": 42,\n  "email": "student@example.com",\n  "user_name": "leanstix"\n}',
            ['400 when credentials are missing, invalid or the account is unavailable.'],
        ),
    },
    ('LogoutView', 'post'): {
        'tag': 'Authentication',
        'summary': 'Log out the current client session',
        'public': True,
        'request_schema': obj({'refresh': string('JWT refresh token to validate before client-side removal.')}, required=['refresh']),
        'responses': {200: response('Logout acknowledgement.', MESSAGE_SCHEMA)},
        'description': markdown(
            'Validates the supplied refresh token and confirms logout.',
            'No access token is required, but a refresh token must be supplied.',
            [
                'The current implementation is stateless and does not blacklist refresh tokens.',
                'Clients must remove both access and refresh tokens after a successful response.',
            ],
            '{\n  "refresh": "eyJ..."\n}',
            '{\n  "message": "Successfully logged out."\n}',
            ['400 when the refresh token is missing, invalid or expired.'],
        ),
    },
    ('GenerateAccessTokenView', 'post'): {
        'tag': 'Authentication',
        'summary': 'Refresh an access token',
        'public': True,
        'request_schema': obj({'refresh': string('Valid JWT refresh token.')}, required=['refresh']),
        'responses': {200: response('A newly issued access token.', obj({'access': string('New access token.')}))},
        'description': markdown(
            'Exchanges a valid refresh token for a new access token.',
            PUBLIC,
            ['The refresh token is validated by SimpleJWT.', 'Only the access token is returned.'],
            '{\n  "refresh": "eyJ..."\n}',
            '{\n  "access": "eyJ..."\n}',
            ['400 when the token is missing, invalid or expired.', '500 for an unexpected token-processing failure.'],
        ),
    },
    ('UserRegistrationView', 'post'): {
        'tag': 'Authentication',
        'summary': 'Register a student account',
        'public': True,
        'request_schema': obj(
            {
                'email': string('Unique account email.', 'student@example.com', fmt=openapi.FORMAT_EMAIL),
                'university_id': string('Unique university or matriculation identifier.', 'UI/2026/1234'),
                'password': string('Password satisfying Django password validators.'),
            },
            required=['email', 'university_id', 'password'],
        ),
        'responses': {201: response('Registration acknowledgement.', MESSAGE_SCHEMA)},
        'description': markdown(
            'Creates an inactive account and sends an activation email.',
            PUBLIC,
            [
                'Email, university ID and password uniqueness/strength are validated.',
                'The account remains inactive until its activation token is accepted.',
                'User creation and activation-email dispatch run as one transaction.',
            ],
            '{\n  "email": "student@example.com",\n  "university_id": "UI/2026/1234",\n  "password": "strong-password"\n}',
            '{\n  "message": "Account created successfully! Please check your email to activate your account."\n}',
            ['400 for duplicate or invalid fields.', '503 when the activation email cannot be sent.'],
        ),
    },
    ('UserActivationView', 'post'): {
        'tag': 'Authentication',
        'summary': 'Activate an account with a token',
        'public': True,
        'request_schema': obj({'token': string('Activation token received by email.')}, required=['token']),
        'responses': {200: response('Activation acknowledgement.', MESSAGE_SCHEMA)},
        'description': markdown(
            'Activates an account using the one-time activation token.',
            PUBLIC,
            ['The token is resolved to a user.', 'Successful activation clears the token and enables login.'],
            '{\n  "token": "activation-token"\n}',
            '{\n  "message": "Account activated successfully!"\n}',
            ['400 when the token is invalid or expired.'],
        ),
    },
    ('ActivateAccountView', 'get'): {
        'tag': 'Authentication',
        'summary': 'Activate an account from a query-string link',
        'public': True,
        'parameters': [query('token', 'Activation token embedded in the activation link.', required=True)],
        'responses': {200: response('Activation acknowledgement.', MESSAGE_SCHEMA)},
        'description': markdown(
            'Alternative activation endpoint intended for links opened directly from email.',
            PUBLIC,
            ['Reads token from the query string.', 'Activates and clears the matching account token.'],
            response_example='{\n  "message": "Account activated successfully!"\n}',
            errors=['400 when the token is invalid or expired.'],
        ),
    },
    ('UserProfileUpdateView', 'put'): {
        'tag': 'Profiles',
        'summary': 'Replace the current user profile fields',
        'description': markdown(
            'Updates the authenticated user’s editable profile.',
            AUTH,
            [
                'Editable fields include names, username, gender, phone, department, year, bio, interests and profile picture.',
                'A multipart profile_picture upload is stored through Cloudinary before the profile is saved.',
                'Email and university ID remain read-only.',
            ],
            errors=['400 for invalid fields or duplicate username.', '500 when profile-picture upload fails.'],
        ),
        'consumes': ['application/json', 'multipart/form-data'],
    },
    ('UserProfileUpdateView', 'patch'): {
        'tag': 'Profiles',
        'summary': 'Update selected current-user profile fields',
        'description': markdown(
            'Partially updates the authenticated user’s editable profile.',
            AUTH,
            [
                'Only supplied fields are changed.',
                'Multipart profile_picture is uploaded before saving.',
                'Email and university ID remain read-only.',
            ],
            errors=['400 for invalid fields.', '500 when profile-picture upload fails.'],
        ),
        'consumes': ['application/json', 'multipart/form-data'],
    },
    ('ChangePasswordView', 'post'): {
        'tag': 'Authentication',
        'summary': 'Change the authenticated user password',
        'request_schema': obj(
            {
                'current_password': string('Existing password.'),
                'new_password': string('Replacement password satisfying Django validators.'),
            },
            required=['current_password', 'new_password'],
        ),
        'responses': {200: response('Password-change acknowledgement.', MESSAGE_SCHEMA)},
        'description': markdown(
            'Changes the password after verifying the existing password.',
            AUTH,
            ['The current password is checked first.', 'The replacement is hashed using Django’s password system.'],
            '{\n  "current_password": "old-password",\n  "new_password": "new-strong-password"\n}',
            '{\n  "message": "Password changed successfully."\n}',
            ['400 when the current password is wrong or the new password fails validation.'],
        ),
    },
    ('PasswordResetRequestView', 'post'): {
        'tag': 'Password reset',
        'summary': 'Request a password-reset email',
        'public': True,
        'request_schema': obj({'email': string('Registered email address.', fmt=openapi.FORMAT_EMAIL)}, required=['email']),
        'responses': {200: response('Reset-email acknowledgement.', MESSAGE_SCHEMA)},
        'description': markdown(
            'Generates a password-reset token and emails a reset link.',
            PUBLIC,
            ['The link contains a URL-safe user ID and a Django password-reset token.', 'The token expires according to Django token rules.'],
            '{\n  "email": "student@example.com"\n}',
            '{\n  "message": "Password reset link sent."\n}',
            ['404 when no account exists for the email.', 'Email-provider failures may surface as server errors.'],
        ),
    },
    ('PasswordResetVerifyView', 'post'): {
        'tag': 'Password reset',
        'summary': 'Verify a password-reset token',
        'public': True,
        'request_schema': obj({'uid': string('URL-safe base64 user ID.'), 'token': string('Password-reset token.')}, required=['uid', 'token']),
        'responses': {200: response('Token validity acknowledgement.', MESSAGE_SCHEMA)},
        'description': markdown(
            'Checks whether a password-reset UID/token pair is still valid.',
            PUBLIC,
            ['No password is changed by this endpoint.', 'Use the completion endpoint after successful verification.'],
            '{\n  "uid": "NDI",\n  "token": "c123-..."\n}',
            '{\n  "message": "Token is valid."\n}',
            ['400 for malformed, invalid or expired tokens.'],
        ),
    },
    ('PasswordResetCompleteView', 'post'): {
        'tag': 'Password reset',
        'summary': 'Complete a password reset',
        'public': True,
        'request_schema': obj(
            {'uid': string('URL-safe base64 user ID.'), 'token': string('Valid reset token.'), 'password': string('New password.')},
            required=['uid', 'token', 'password'],
        ),
        'responses': {200: response('Password-reset acknowledgement.', MESSAGE_SCHEMA)},
        'description': markdown(
            'Replaces the user password after validating the reset token.',
            PUBLIC,
            ['The password is hashed before persistence.', 'The token becomes invalid after the password changes.'],
            '{\n  "uid": "NDI",\n  "token": "c123-...",\n  "password": "new-password"\n}',
            '{\n  "message": "Password has been reset successfully."\n}',
            ['400 for malformed, invalid or expired tokens.'],
        ),
    },
    ('SearchUserView', 'get'): {
        'tag': 'Friendships',
        'summary': 'Search other Flow users',
        'parameters': [query('q', 'Required username or email search fragment. A leading @ may be removed by clients.', required=True)],
        'description': markdown(
            'Searches active user records by username or email.',
            AUTH,
            ['The authenticated user is excluded from results.', 'Matching is case-insensitive and partial.'],
            response_example='[\n  {"id": 7, "user_name": "friend", "email": "friend@example.com"}\n]',
            errors=['400 when q is empty.'],
        ),
    },
    ('ViewFriendsView', 'get'): {
        'tag': 'Friendships',
        'summary': 'List accepted friends',
        'description': markdown(
            'Returns users connected to the authenticated user through accepted friend requests.',
            AUTH,
            ['Both outgoing and incoming accepted requests are considered.', 'Each friend may include an existing conversation ID.'],
            response_example='[\n  {"id": 7, "user_name": "friend", "conversation_id": 12}\n]',
        ),
    },
    ('FriendRequestView', 'get'): {
        'tag': 'Friendships',
        'summary': 'List incoming pending friend requests',
        'description': markdown(
            'Returns unresolved requests addressed to the authenticated user.',
            AUTH,
            ['Accepted requests are excluded.', 'Only the recipient can see the pending request.'],
            response_example='[\n  {"id": 9, "accepted": false, "from_user": {"id": 7}}\n]',
        ),
    },
    ('FriendRequestView', 'post'): {
        'tag': 'Friendships',
        'summary': 'Send a friend request',
        'request_schema': obj({'to_user_id': integer('Recipient user ID.', 7)}, required=['to_user_id']),
        'description': markdown(
            'Creates a pending friend request and notifies the recipient.',
            AUTH,
            ['Self-requests are rejected.', 'A duplicate request is not created.', 'A realtime friend-request notification is sent.'],
            '{\n  "to_user_id": 7\n}',
            errors=['400 for missing, self or duplicate requests.', '404 when the recipient does not exist.'],
        ),
    },
    ('FriendRequestView', 'patch'): {
        'tag': 'Friendships',
        'summary': 'Accept an incoming friend request',
        'responses': {200: response('Acceptance details.', obj({'message': string(), 'from_user_id': integer(), 'to_user_id': integer()}))},
        'description': markdown(
            'Accepts a pending request addressed to the authenticated user.',
            AUTH,
            ['The request is selected by URL ID and recipient.', 'The sender receives a friend-accepted notification.'],
            response_example='{\n  "message": "Friend request accepted.",\n  "from_user_id": 7,\n  "to_user_id": 42\n}',
            errors=['404 when the request is absent or belongs to another recipient.'],
        ),
    },
    ('UserProfileView', 'get'): {
        'tag': 'Profiles',
        'summary': 'Retrieve a user profile',
        'description': markdown(
            'Returns the public profile fields for a user selected by numeric ID.',
            AUTH,
            ['The response includes user_id, email and serialized profile fields.', 'No authentication token is returned by this endpoint.'],
            errors=['404 when the user does not exist.'],
        ),
    },
    ('PostView', 'get'): {
        'tag': 'Posts',
        'summary': 'List the current user’s posts',
        'description': markdown(
            'Returns posts authored by the authenticated user.',
            AUTH,
            ['Results include media, hashtags, mentions, repost source and engagement counts.', 'Posts are ordered newest first.'],
        ),
    },
    ('PostView', 'post'): {
        'tag': 'Posts',
        'summary': 'Create a text, image or video post',
        'consumes': ['application/json', 'multipart/form-data'],
        'description': markdown(
            'Creates a post and extracts hashtags and @username mentions.',
            AUTH,
            [
                'Send content as JSON for text-only posts.',
                'For media posts use multipart/form-data with content, platform, repeated media fields and JSON media_metadata.',
                'A post accepts up to four images or one video; images and video cannot be mixed.',
                'Mobile video must already be edited on the client and may be at most 180 seconds; web video may be at most 90 seconds.',
                'Mentioned users receive notifications after the post is saved.',
            ],
            request_example='{\n  "content": "Building #CampusTech with @friend"\n}',
            errors=['400 for empty posts, unsupported media, excessive count, size or duration.', '413 when upstream infrastructure rejects an oversized upload.'],
            notes=['media_metadata is a JSON array aligned by index with repeated media files.'],
        ),
    },
    ('PostView', 'delete'): {
        'tag': 'Posts',
        'summary': 'Delete one of the current user’s posts',
        'responses': {204: response('Post deleted; no response body.')},
        'description': markdown(
            'Permanently deletes a post authored by the authenticated user.',
            AUTH,
            ['Associated likes, comments, media relations and notifications cascade according to model rules.'],
            errors=['400 when post_id is missing.', '404 when the post does not exist or belongs to another user.'],
        ),
    },
    ('SearchPostsView', 'get'): {
        'tag': 'Posts',
        'summary': 'Search posts outside the current user’s posts',
        'parameters': [query('q', 'Required phrase, username, email fragment or hashtag.', required=True), *PAGINATION_PARAMETERS],
        'description': markdown(
            'Searches posts by text, author identity or hashtag.',
            AUTH,
            ['A query beginning with # performs an exact hashtag match.', 'The authenticated user’s own posts are excluded.', 'Duplicate rows are removed.'],
            errors=['400 when q is empty.'],
        ),
    },
    ('SearchUserPostsView', 'get'): {
        'tag': 'Posts',
        'summary': 'Search the current user’s posts',
        'parameters': [query('q', 'Optional content or hashtag search phrase.'), *PAGINATION_PARAMETERS],
        'description': markdown(
            'Searches only posts authored by the authenticated user.',
            AUTH,
            ['With no q value, all current-user posts are returned newest first.'],
        ),
    },
    ('HashtagSearchView', 'get'): {
        'tag': 'Posts',
        'summary': 'Search and rank hashtags',
        'parameters': [query('q', 'Optional hashtag fragment; a leading # is ignored.')],
        'description': markdown(
            'Returns hashtag suggestions ranked by post usage.',
            AUTH,
            ['Matching is case-insensitive and partial.', 'At most 30 hashtag records are returned.'],
            response_example='[\n  {"name": "campustech", "posts_count": 12}\n]',
        ),
    },
    ('HashtagPostsView', 'get'): {
        'tag': 'Posts',
        'summary': 'List posts for a hashtag',
        'parameters': PAGINATION_PARAMETERS,
        'description': markdown(
            'Returns posts assigned to the hashtag in the URL.',
            AUTH,
            ['A leading # in the URL value is ignored.', 'Matching is case-insensitive.', 'Results are newest first.'],
        ),
    },
    ('FeedView', 'get'): {
        'tag': 'Posts',
        'summary': 'Get the friends feed',
        'description': markdown(
            'Returns posts authored by the current user and accepted friends.',
            AUTH,
            ['Posts are ranked by combined likes, comments and reposts, then recency.'],
        ),
    },
    ('AllFeedView', 'get'): {
        'tag': 'Posts',
        'summary': 'Get the campus-wide feed',
        'parameters': PAGINATION_PARAMETERS,
        'description': markdown(
            'Returns the global Flow post feed.',
            AUTH,
            ['Posts are ranked by combined engagement and recency.', 'The response is paginated.'],
        ),
    },
    ('CreateRoomView', 'post'): {
        'tag': 'Calls',
        'summary': 'Create an open call room',
        'request_schema': obj({'call_type': string('Call media type.', 'video', ['audio', 'video'])}),
        'description': markdown(
            'Creates an immediately active call room for backward-compatible room-code flows.',
            AUTH,
            ['The creator is added as the first participant.', 'The room starts in active state.'],
            '{\n  "call_type": "video"\n}',
            errors=['400 when call_type is not audio or video.'],
        ),
    },
    ('JoinRoomView', 'post'): {
        'tag': 'Calls',
        'summary': 'Join or accept an invitation to a call room',
        'description': markdown(
            'Joins an open room by code or accepts an existing invitation.',
            AUTH,
            ['Ended calls cannot be joined.', 'Invitation-only rooms reject users without an invitation.', 'Room and participant websocket state is broadcast after joining.'],
            errors=['403 when the user was not invited.', '404 when the room does not exist.', '409 when the call has ended.'],
        ),
    },
    ('DirectCallView', 'post'): {
        'tag': 'Calls',
        'summary': 'Start a direct audio or video call',
        'request_schema': obj(
            {
                'recipient_id': integer('User to call.', 7),
                'conversation_id': integer('Optional conversation linking the call.', 12),
                'call_type': string('audio or video.', 'audio', ['audio', 'video']),
            },
            required=['recipient_id', 'call_type'],
        ),
        'description': markdown(
            'Creates a ringing call and sends a realtime incoming-call event to the recipient.',
            AUTH,
            ['Self-calls are rejected.', 'When conversation_id is supplied, both caller and recipient must belong to it.', 'The caller invitation is accepted immediately; the recipient invitation starts as ringing.'],
            '{\n  "recipient_id": 7,\n  "conversation_id": 12,\n  "call_type": "video"\n}',
            errors=['400 for invalid recipients, call types or conversation mismatch.', '404 when the recipient or conversation does not exist.'],
        ),
    },
    ('IncomingCallsView', 'get'): {
        'tag': 'Calls',
        'summary': 'List incoming ringing calls',
        'description': markdown(
            'Returns calls where the authenticated user has a ringing invitation.',
            AUTH,
            ['Only ringing or active rooms are included.', 'Clients normally combine this endpoint with the private call websocket.'],
        ),
    },
    ('CallDetailView', 'get'): {
        'tag': 'Calls',
        'summary': 'Retrieve call-room state',
        'description': markdown(
            'Returns the current state of a call room.',
            AUTH,
            ['Only current room participants can retrieve the room.', 'Participants and invitations are included.'],
            errors=['404 when the room does not exist or the user is not a participant.'],
        ),
    },
    ('AcceptCallView', 'post'): {
        'tag': 'Calls',
        'summary': 'Accept an incoming call',
        'description': markdown(
            'Marks the current user’s invitation accepted and activates the room.',
            AUTH,
            ['Call state is broadcast to room and user websocket channels.', 'started_at is set once.'],
            errors=['404 when the room or invitation is unavailable.', '409 when the call is no longer active.'],
        ),
    },
    ('RejectCallView', 'post'): {
        'tag': 'Calls',
        'summary': 'Reject an incoming call',
        'description': markdown(
            'Marks the current user’s invitation rejected.',
            AUTH,
            ['The room is marked rejected when no other ringing/accepted invitees remain.', 'The caller and room receive realtime state updates.'],
            errors=['404 when the room or invitation is unavailable.'],
        ),
    },
    ('InviteParticipantsView', 'post'): {
        'tag': 'Calls',
        'summary': 'Invite more participants to an active call',
        'request_schema': obj({'user_ids': array(integer('User ID.'), 'Unique user IDs to invite.')}, required=['user_ids']),
        'description': markdown(
            'Adds users to a ringing or active call, up to the eight-participant limit.',
            AUTH,
            ['Only accepted active participants can add people to invitation-based calls.', 'Duplicate and existing participant IDs are ignored.', 'Each new user receives a private incoming-call event.'],
            '{\n  "user_ids": [7, 8]\n}',
            errors=['400 for invalid IDs, unavailable users or exceeding eight participants.', '403 when the inviter is not an active participant.', '409 when the call has ended.'],
        ),
    },
    ('LeaveCallView', 'post'): {
        'tag': 'Calls',
        'summary': 'Leave or end a call',
        'responses': {200: response('Leave result.', obj({'detail': string(), 'status': string(enum=['active', 'ended'])}))},
        'description': markdown(
            'Removes the authenticated user from a call room.',
            AUTH,
            ['The invitation is marked left.', 'The room ends when the creator leaves or too few accepted participants remain.', 'Otherwise a participant-left event is broadcast.'],
            response_example='{\n  "detail": "You left the call.",\n  "status": "ended"\n}',
            errors=['404 when the user is not a participant.'],
        ),
    },
}


ACTION_DOCS = {
    ('AdvertisementViewSet', 'mine'): {
        'tag': 'Marketplace',
        'summary': 'List the current seller’s listings',
        'parameters': PAGINATION_PARAMETERS,
        'description': markdown('Returns marketplace listings owned by the authenticated user.', AUTH, ['Archived records may be included for seller management.', 'Standard marketplace pagination applies.']),
    },
    ('AdvertisementViewSet', 'saved'): {
        'tag': 'Marketplace',
        'summary': 'List saved marketplace listings',
        'parameters': PAGINATION_PARAMETERS,
        'description': markdown('Returns listings saved by the authenticated user.', AUTH, ['Only records with a SavedAdvertisement relation for the viewer are returned.']),
    },
    ('AdvertisementViewSet', 'save_listing'): {
        'tag': 'Marketplace',
        'summary': 'Save a marketplace listing',
        'responses': {200: response('Listing was already saved.', obj({'saved': openapi.Schema(type=openapi.TYPE_BOOLEAN)})), 201: response('Listing was newly saved.', obj({'saved': openapi.Schema(type=openapi.TYPE_BOOLEAN)}))},
        'description': markdown('Adds a listing to the current user’s saved items.', AUTH, ['Saving is idempotent.', 'A seller cannot save their own listing.'], response_example='{\n  "saved": true\n}', errors=['400 when attempting to save the current user’s own listing.', '404 when the listing does not exist.']),
    },
    ('AdvertisementViewSet', 'unsave'): {
        'tag': 'Marketplace',
        'summary': 'Remove a saved marketplace listing',
        'responses': {204: response('Saved relation removed; no response body.')},
        'description': markdown('Removes the current user’s saved relation for a listing.', AUTH, ['The operation succeeds even when the relation is already absent.'], errors=['404 when the listing does not exist.']),
    },
    ('AdvertisementViewSet', 'report'): {
        'tag': 'Marketplace',
        'summary': 'Report a marketplace listing',
        'request_schema': obj({'reason': string('Moderation reason, up to the serializer limit.')}, required=['reason']),
        'description': markdown('Creates or updates the current user’s moderation report for a listing.', AUTH, ['A user cannot report their own listing.', 'Repeated reports update the existing reason instead of duplicating the report.'], '{\n  "reason": "Misleading item description"\n}', errors=['400 for an invalid reason or self-report.', '404 when the listing does not exist.']),
    },
    ('AdvertisementViewSet', 'set_status'): {
        'tag': 'Marketplace',
        'summary': 'Change seller listing status',
        'request_schema': obj({'status': string('New listing status.', 'reserved', ['active', 'reserved', 'sold', 'archived'])}, required=['status']),
        'description': markdown('Changes a listing’s lifecycle status.', AUTH, ['Only the seller or staff may change status.', 'updated_at is refreshed.'], '{\n  "status": "sold"\n}', errors=['400 for an unsupported status.', '403 for non-owners.', '404 when the listing does not exist.']),
    },
    ('AdvertisementViewSet', 'contact_seller'): {
        'tag': 'Marketplace',
        'summary': 'Start a listing-aware seller conversation',
        'request_schema': obj({'message': string('Optional first enquiry; a default is generated when blank.')}, required=[]),
        'description': markdown('Creates or reuses a direct conversation with the seller and sends a listing attachment.', AUTH, ['The first message stores listing ID, title, price, currency, image, status and navigation routes.', 'The seller can open the exact item from the message card.', 'A buyer cannot contact themselves about their own listing.', 'Message receipts, notifications and websocket broadcasts are created normally.'], '{\n  "message": "Is this still available?"\n}', response_example='{\n  "conversation": {"id": 12},\n  "message": {"id": 44, "attachments": [{"kind": "listing"}]}\n}', errors=['400 for self-contact or a message longer than 5000 characters.', '404 when the listing does not exist.']),
    },
    ('CommunityViewSet', 'join'): {
        'tag': 'Communities',
        'summary': 'Join or request access to a community',
        'description': markdown('Creates a community membership for the authenticated user.', AUTH, ['Public communities activate membership immediately.', 'Private communities create a pending request and notify the owner.', 'Repeated calls return the existing membership state.'], response_example='{\n  "detail": "Joined successfully.",\n  "status": "active"\n}', errors=['404 when the community does not exist.']),
    },
    ('CommunityViewSet', 'leave'): {
        'tag': 'Communities',
        'summary': 'Leave a community',
        'responses': {204: response('Membership deleted; no response body.')},
        'description': markdown('Deletes the current user’s non-owner community membership.', AUTH, ['Owners cannot leave until ownership is transferred.'], errors=['400 when the user is not a member or is the owner.', '404 when the community does not exist.']),
    },
    ('CommunityViewSet', 'members'): {
        'tag': 'Communities',
        'summary': 'List community members and pending requests',
        'description': markdown('Returns membership records for a community.', AUTH, ['Private rosters are visible only to members and staff.', 'Moderators see pending records; ordinary users see active members only.'], errors=['403 when a private roster is requested by a non-member.', '404 when the community does not exist.']),
    },
    ('CommunityViewSet', 'approve_member'): {
        'tag': 'Communities',
        'summary': 'Approve a pending community member',
        'description': markdown('Activates a pending private-community membership.', AUTH, ['Only owners and moderators may approve.', 'The approved user receives a notification.'], errors=['400 when the pending membership does not exist.', '403 when the actor cannot moderate.', '404 when the community does not exist.']),
    },
    ('CommunityViewSet', 'update_member_role'): {
        'tag': 'Communities',
        'summary': 'Change a community member role',
        'request_schema': obj({'role': string('member or moderator.', 'moderator', ['member', 'moderator'])}, required=['role']),
        'description': markdown('Changes an active member between member and moderator roles.', AUTH, ['Only the community owner or staff may change roles.', 'The owner role cannot be changed through this endpoint.'], '{\n  "role": "moderator"\n}', errors=['400 for invalid role or membership state.', '403 when the actor is not the owner.', '404 when the community does not exist.']),
    },
    ('CommunityPostViewSet', 'toggle_pin'): {
        'tag': 'Community posts',
        'summary': 'Toggle a community post pin',
        'description': markdown('Pins or unpins a community post.', AUTH, ['Only community owners and moderators may pin content.', 'The response returns the updated post.'], errors=['403 when the actor cannot moderate.', '404 when the post is unavailable.']),
    },
    ('CommunityResourceViewSet', 'toggle_pin'): {
        'tag': 'Community resources',
        'summary': 'Toggle a community resource pin',
        'description': markdown('Pins or unpins a community resource.', AUTH, ['Only community owners and moderators may pin resources.', 'The response returns the updated resource.'], errors=['403 when the actor cannot moderate.', '404 when the resource is unavailable.']),
    },
    ('ConversationViewSet', 'messages'): {
        'tag': 'Messaging',
        'summary': 'List the latest messages in a conversation',
        'description': markdown('Returns up to the latest 50 messages in chronological display order.', AUTH, ['The requester must be a participant.', 'Unread receipts for the requester are marked delivered when messages are fetched.', 'Replies and typed attachments are embedded in each message.'], errors=['404 when the conversation is unavailable to the user.']),
    },
    ('ConversationViewSet', 'send_message'): {
        'tag': 'Messaging',
        'summary': 'Send a message or typed attachment',
        'consumes': ['application/json', 'multipart/form-data'],
        'description': markdown('Creates a message inside a conversation.', AUTH, ['The requester must be a participant.', 'A message may contain text, files, structured attachment metadata or both.', 'attachment_type must be one of image, video, audio, document, contact, location or listing.', 'File uploads use repeated files fields; structured attachments use attachment_payload.', 'Receipts, notifications and message.created websocket events are created after transaction commit.'], request_example='{\n  "content": "Here are the notes",\n  "reply_to": 41\n}', errors=['400 when content and attachments are both empty, attachment type is missing, files are unsupported/oversized, or reply_to belongs to another conversation.', '404 when the conversation is unavailable.'], notes=['For multipart requests, attachment_payload is JSON text.']),
    },
    ('ConversationViewSet', 'mark_read'): {
        'tag': 'Messaging',
        'summary': 'Mark conversation messages read',
        'responses': {200: response('Number of receipts updated.', COUNT_SCHEMA)},
        'description': markdown('Marks all unread receipts for the authenticated participant as delivered and read.', AUTH, ['Aggregate message read status is updated when every recipient has read.', 'Realtime receipt events are broadcast to the conversation.'], response_example='{\n  "updated_count": 5\n}', errors=['404 when the conversation is unavailable.']),
    },
    ('NotificationViewSet', 'mark_read'): {
        'tag': 'Notifications',
        'summary': 'Mark one notification read',
        'description': markdown('Marks one recipient-owned notification as read.', AUTH, ['The operation is idempotent.', 'The updated notification is returned.'], errors=['404 when the notification does not belong to the user.']),
    },
    ('NotificationViewSet', 'mark_all_read'): {
        'tag': 'Notifications',
        'summary': 'Mark all notifications read',
        'responses': {200: response('Number of notifications updated.', COUNT_SCHEMA)},
        'description': markdown('Marks every unread notification belonging to the current user as read.', AUTH, ['Other users’ notifications are never touched.'], response_example='{\n  "updated_count": 9\n}'),
    },
    ('NotificationViewSet', 'unread_count'): {
        'tag': 'Notifications',
        'summary': 'Get unread notification count',
        'responses': {200: response('Unread total.', obj({'unread_count': integer('Unread notification count.', 4)}))},
        'description': markdown('Returns the current user’s unread notification total.', AUTH, ['Useful for navigation badges and polling fallbacks.'], response_example='{\n  "unread_count": 4\n}'),
    },
}


PATH_DOCS = [
    (
        re.compile(r'/api/posts/\{post_id\}/comments/?$'),
        'get',
        {
            'tag': 'Comments',
            'summary': 'List top-level comments for a post',
            'parameters': PAGINATION_PARAMETERS,
            'description': markdown('Returns root comments for one post.', AUTH, ['Only comments with no parent are returned.', 'Each root includes the total descendant reply count.', 'Use the thread replies endpoint to load the complete flat descendant thread.'], errors=['404 when the post does not exist.']),
        },
    ),
    (
        re.compile(r'/api/posts/\{post_id\}/like/?$'),
        'post',
        {
            'tag': 'Posts',
            'summary': 'Toggle a post like',
            'responses': {200: response('Current like state and count.', obj({'liked': openapi.Schema(type=openapi.TYPE_BOOLEAN), 'likes_count': integer()}))},
            'description': markdown('Likes an unliked post or removes the current user’s existing like.', AUTH, ['Like creation is unique per user and post.', 'The post author receives a notification only when a like is added.', 'Self-notifications are suppressed by the notification service.'], response_example='{\n  "liked": true,\n  "likes_count": 12\n}', errors=['404 when the post does not exist.']),
        },
    ),
    (
        re.compile(r'/api/posts/\{post_id\}/comment/?$'),
        'post',
        {
            'tag': 'Comments',
            'summary': 'Add a top-level comment',
            'request_schema': obj({'content': string('Comment text, up to 5000 characters.')}, required=['content']),
            'description': markdown('Creates a root comment on a post.', AUTH, ['Hashtag-like text is preserved as content.', '@username mentions are resolved and notified.', 'The post author receives a comment notification.'], '{\n  "content": "Great work @friend"\n}', errors=['400 for empty or oversized content.', '404 when the post does not exist.']),
        },
    ),
    (
        re.compile(r'/api/posts/\{post_id\}/repost/?$'),
        'post',
        {
            'tag': 'Posts',
            'summary': 'Repost or quote a post',
            'request_schema': obj({'content': string('Optional quote text. Original content is used when omitted.')}),
            'description': markdown('Creates a new post linked to the source post.', AUTH, ['Optional quote content is indexed for hashtags and mentions.', 'The original author receives a repost notification.'], '{\n  "content": "Worth reading #CampusTech"\n}', errors=['404 when the source post does not exist.']),
        },
    ),
    (
        re.compile(r'/api/posts/\{post_id\}/delete/?$'),
        'delete',
        {
            'tag': 'Posts',
            'summary': 'Delete the current user’s post',
            'responses': {204: response('Post deleted; no response body.')},
            'description': markdown('Deletes a post only when the authenticated user is its author.', AUTH, ['This is the URL-specific form of PostView.delete.'], errors=['404 when the post does not exist or belongs to another user.']),
        },
    ),
    (
        re.compile(r'/api/posts/\{post_id\}/report/?$'),
        'post',
        {
            'tag': 'Posts',
            'summary': 'Report a post',
            'request_schema': obj({'reason': string('Required moderation reason.')}, required=['reason']),
            'description': markdown('Creates a moderation report for a post.', AUTH, ['The reason is trimmed before persistence.'], '{\n  "reason": "Harassment"\n}', errors=['400 when reason is empty.', '404 when the post does not exist.']),
        },
    ),
    (
        re.compile(r'/api/posts/comments/\{comment_id\}/reply/?$'),
        'post',
        {
            'tag': 'Comments',
            'summary': 'Reply to any comment or reply',
            'request_schema': obj({'content': string('Reply text, up to 5000 characters.')}, required=['content']),
            'description': markdown('Creates a child reply at any thread depth.', AUTH, ['The parent may itself be a reply.', 'root and depth are calculated automatically.', 'Mentioned users, the parent author and the post author are notified without duplicate notifications.'], '{\n  "content": "Replying to @friend"\n}', errors=['400 for empty or oversized content.', '404 when the parent comment does not exist.']),
        },
    ),
    (
        re.compile(r'/api/posts/comments/\{comment_id\}/replies/?$'),
        'get',
        {
            'tag': 'Comments',
            'summary': 'Load a complete flat comment thread',
            'parameters': PAGINATION_PARAMETERS,
            'description': markdown('Returns every descendant reply beneath the selected root thread.', AUTH, ['Passing any comment in the thread resolves its root.', 'Replies are ordered oldest first.', 'Clients rebuild unlimited nesting from parent, root and depth fields.'], response_example='{\n  "root_id": 10,\n  "count": 3,\n  "results": [{"id": 11, "parent": 10, "depth": 1}]\n}', errors=['404 when the comment does not exist.']),
        },
    ),
    (
        re.compile(r'/api/posts/comments/\{comment_id\}/delete/?$'),
        'delete',
        {
            'tag': 'Comments',
            'summary': 'Delete the current user’s comment',
            'responses': {204: response('Comment deleted; no response body.')},
            'description': markdown('Deletes a comment or reply authored by the authenticated user.', AUTH, ['Child replies cascade according to the comment model’s foreign-key rule.'], errors=['404 when the comment does not exist or belongs to another user.']),
        },
    ),
]


class FlowAutoSchema(SwaggerAutoSchema):
    """Consistent rich ReDoc documentation for every generated Flow operation."""

    def _lookup_doc(self):
        view_name = self.view.__class__.__name__
        action = getattr(self.view, 'action', None) or self.method.lower()

        explicit = CUSTOM_DOCS.get((view_name, action)) or ACTION_DOCS.get((view_name, action))
        if explicit:
            return explicit

        standard = standard_resource_doc(view_name, action)
        if standard:
            return standard

        for pattern, method, documentation in PATH_DOCS:
            if method == self.method.lower() and pattern.search(self.path):
                return documentation

        return None

    def get_summary_and_description(self):
        documentation = self._lookup_doc()
        if documentation:
            return documentation.get('summary'), documentation.get('description', '')

        summary, description = super().get_summary_and_description()
        if not summary:
            action = getattr(self.view, 'action', None) or self.method.lower()
            summary = f'{action.replace("_", " ").title()}'
        if not description:
            description = markdown(
                'Performs the documented Flow API operation.',
                AUTH,
                ['Request and response fields are described by the generated schema below.'],
                errors=['400 for invalid input.', '401 when authentication is missing or expired.'],
            )
        return summary, description

    def get_tags(self, operation_keys=None):
        documentation = self._lookup_doc()
        if documentation and documentation.get('tag'):
            return [documentation['tag']]
        return super().get_tags(operation_keys)

    def get_security(self):
        documentation = self._lookup_doc()
        permission_names = {permission.__name__ for permission in getattr(self.view, 'permission_classes', [])}
        if documentation and documentation.get('public'):
            return []
        if 'AllowAny' in permission_names:
            return []
        return [{'Bearer': []}]

    def get_request_serializer(self):
        documentation = self._lookup_doc()
        if documentation and documentation.get('request_schema') is not None:
            return documentation['request_schema']
        return super().get_request_serializer()

    def add_manual_parameters(self, parameters):
        parameters = super().add_manual_parameters(parameters)
        documentation = self._lookup_doc()
        if not documentation:
            return parameters

        existing = {(parameter.name, parameter.in_) for parameter in parameters}
        for parameter in documentation.get('parameters', []):
            key = (parameter.name, parameter.in_)
            if key not in existing:
                parameters.append(parameter)
                existing.add(key)
        return parameters

    def get_responses(self):
        responses = super().get_responses()
        documentation = self._lookup_doc() or {}

        for status_code, documented_response in documentation.get('responses', {}).items():
            responses[str(status_code)] = documented_response

        public = documentation.get('public') or any(
            permission.__name__ == 'AllowAny'
            for permission in getattr(self.view, 'permission_classes', [])
        )
        if not public and '401' not in responses:
            responses['401'] = response('Authentication failed or the Bearer access token is missing/expired.', ERROR_SCHEMA)
        if self.method.lower() in {'post', 'put', 'patch'} and '400' not in responses:
            responses['400'] = response('Submitted data or query parameters failed validation.', ERROR_SCHEMA)
        if self.method.lower() in {'put', 'patch', 'delete'} and '403' not in responses:
            responses['403'] = response('The authenticated user does not have permission for this operation.', ERROR_SCHEMA)
        if ('{' in self.path or getattr(self.view, 'detail', False)) and '404' not in responses:
            responses['404'] = response('The requested resource was not found or is outside the permitted queryset.', ERROR_SCHEMA)
        if self.method.lower() == 'post' and any(value in self.path for value in ('/call/', '/join-room/')) and '409' not in responses:
            responses['409'] = response('The requested state transition conflicts with the current call state.', ERROR_SCHEMA)

        return responses

    def get_consumes(self):
        documentation = self._lookup_doc()
        if documentation and documentation.get('consumes'):
            return documentation['consumes']
        return super().get_consumes()

    def is_deprecated(self):
        if self.path.startswith('/api/adds/'):
            return True
        documentation = self._lookup_doc()
        if documentation and documentation.get('deprecated') is not None:
            return documentation['deprecated']
        return super().is_deprecated()
