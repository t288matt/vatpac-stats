# Architecture Principles

## Core Principles

### 1. Maintainability
- Code must be easy to understand, modify, and extend
- Clear naming conventions and consistent coding standards
- Modular design that allows for easy updates and bug fixes
- Comprehensive error handling and logging

### 2. Service-Based Architecture
- Clear separation between different functional areas
- Each service has a single, well-defined responsibility
- Services communicate through well-defined interfaces
- Loose coupling between services

### 3. Separation of Duties
- Data access layer separate from business logic
- Business logic separate from presentation/API layer
- Configuration separate from application code
- Each component has a single, clear purpose

### 4. Supportability
- Comprehensive logging and monitoring
- Clear error messages and debugging information
- Easy troubleshooting and problem identification
- Well-documented operational procedures

### 5. Docker-Based Application
- Containerize all application components
- Use Docker Compose for local development and testing
- Ensure consistent environments across development, staging, and production
- Keep containers lightweight and focused on single responsibilities

### 6. PostgreSQL Database
- Use PostgreSQL as the primary data store
- Proper database design with normalized schemas
- Efficient queries and indexing strategies
- Database migrations and version control

### 7. Python Coding Standards
- Follow PEP 8 style guidelines
- Type hints where appropriate
- Comprehensive unit and integration tests
- Clear function and class documentation
- All datetime operations use UTC timezone throughout the project

### 8. Well-Documented
- API documentation with clear examples
- Code comments explaining complex logic
- README files for setup and usage
- Architecture diagrams and data flow documentation

### 9. Minimal Complexity
- **Simple is best** - avoid over-engineering
- Prefer straightforward solutions over clever ones
- Reduce dependencies and external libraries where possible
- Clear, readable code over performance optimizations (unless required)

## Implementation Guidelines

### Time Handling
- **UTC Throughout**: All datetime operations, storage, and API responses use UTC timezone
- **No Local Time**: Never store or process local time - convert to UTC immediately
- **Consistent Format**: Use UTC format (YYYY-MM-DD HH:MM:SS) for all timestamps
- **Timezone Awareness**: All datetime objects must be timezone-aware with UTC timezone
- **Database Storage**: Store all timestamps in UTC in PostgreSQL
- **API Responses**: Return all timestamps in UTC format
- **Logging**: Log all timestamps in UTC

### Code Organization
```
src/
├── services/          # Business logic services
├── models/            # Data models and database schemas
├── api/               # API endpoints and controllers
├── database/          # Database connection and migrations
├── utils/             # Shared utilities and helpers
└── config/            # Configuration management
```

### Service Design
- Each service should be independently testable
- Services should have clear input/output contracts
- Error handling should be consistent across services
- Logging should be comprehensive but not excessive

### Database Design
- Use migrations for schema changes
- Implement proper indexing strategies
- Design for query performance from the start
- Use transactions appropriately for data consistency
- Store all timestamps in UTC timezone
- Use TIMESTAMPTZ (timestamp with timezone) for all datetime columns

### Testing Strategy
- Unit tests for individual functions and methods
- Integration tests for service interactions
- End-to-end tests for complete workflows
- Test data should be realistic and maintainable

### Documentation Standards
- Inline code documentation for complex logic
- API documentation with request/response examples
- Setup and deployment instructions
- Troubleshooting guides for common issues

## Anti-Patterns to Avoid

- **Over-abstraction**: Don't create abstractions until you need them
- **Premature optimization**: Focus on correctness first, performance second
- **Complex inheritance hierarchies**: Prefer composition over inheritance
- **Tight coupling**: Services should not directly depend on each other's internals
- **Hardcoded values**: Use configuration files and environment variables
- **Mixed timezones**: Never mix UTC and local time in the same system
- **Naive datetimes**: Never use timezone-naive datetime objects

## Success Metrics

- Code can be understood by new team members within a day
- Bugs can be identified and fixed within hours, not days
- New features can be added without breaking existing functionality
- System can be deployed and configured with minimal manual steps
- Performance meets requirements without complex optimizations
