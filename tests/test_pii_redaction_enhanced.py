"""Comprehensive tests for enhanced PII redaction with multi-pass validation."""

import pytest
from core.privacy import PiiRedactor


class TestEnhancedPIIRedaction:
    """Test suite for the enhanced PII redaction system."""

    def test_redact_aws_access_keys(self):
        """Verify AWS access keys are redacted."""
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "AKIAIOSFODNN7EXAMPLE" not in result.text
        assert "[REDACTED]" in result.text
        assert result.replacements.get("aws_access_key", 0) > 0

    def test_redact_aws_secret_keys(self):
        """Verify AWS secret keys are redacted."""
        text = 'aws_secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in result.text
        assert "[REDACTED]" in result.text

    def test_redact_azure_keys(self):
        """Verify Azure keys are redacted."""
        text = 'azure_storage_key="1234567890abcdef1234567890abcdef1234567890abcdef"'
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "1234567890abcdef" not in result.text
        assert "[REDACTED]" in result.text

    def test_redact_jwt_tokens(self):
        """Verify JWT tokens are redacted."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result.text
        assert "[REDACTED]" in result.text
        assert result.replacements.get("jwt", 0) > 0

    def test_redact_database_connections(self):
        """Verify database connection strings are redacted."""
        text = "mongodb://user:password@localhost:27017/mydb"
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "mongodb://user:password@localhost:27017/mydb" not in result.text
        assert "[REDACTED]" in result.text

    def test_redact_postgresql_connections(self):
        """Verify PostgreSQL connection strings are redacted."""
        text = "postgresql://dbuser:secretpass@database.server.com:5432/mydb"
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "secretpass" not in result.text
        assert "[REDACTED]" in result.text

    def test_redact_private_keys(self):
        """Verify private keys are redacted."""
        text = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7VJTUt9Us8cKj
-----END PRIVATE KEY-----"""
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "-----BEGIN PRIVATE KEY-----" not in result.text
        assert "[REDACTED]" in result.text

    def test_redact_ssh_keys(self):
        """Verify SSH keys are redacted."""
        text = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7VJTUt9Us8cKjMzEa user@host"
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "AAAAB3NzaC1yc2EAAAADAQABAAABAQC7VJTUt9Us8cKjMzEa" not in result.text
        assert "[REDACTED]" in result.text

    def test_redact_ipv4_addresses(self):
        """Verify IPv4 addresses are redacted."""
        text = "Server IP: 192.168.1.100"
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "192.168.1.100" not in result.text
        assert "[REDACTED]" in result.text

    def test_redact_ipv6_addresses(self):
        """Verify IPv6 addresses are redacted."""
        text = "IPv6: 2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "2001:0db8:85a3:0000:0000:8a2e:0370:7334" not in result.text
        assert "[REDACTED]" in result.text

    def test_redact_urls_with_credentials(self):
        """Verify URLs containing credentials are redacted."""
        text = "https://user:password@api.example.com/endpoint"
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "user:password" not in result.text
        assert "[REDACTED]" in result.text

    def test_redact_email_addresses(self):
        """Verify email addresses are redacted."""
        text = "Contact: admin@company.com"
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "admin@company.com" not in result.text
        assert "[REDACTED]" in result.text

    def test_redact_phone_numbers(self):
        """Verify phone numbers are redacted."""
        text = "Phone: +1-555-123-4567"
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "555-123-4567" not in result.text
        assert "[REDACTED]" in result.text

    def test_redact_ssn(self):
        """Verify SSNs are redacted."""
        text = "SSN: 123-45-6789"
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "123-45-6789" not in result.text
        assert "[REDACTED]" in result.text

    def test_redact_credit_cards(self):
        """Verify credit card numbers are redacted."""
        text = "Card: 4532-1234-5678-9010"
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "4532-1234-5678-9010" not in result.text
        assert "[REDACTED]" in result.text

    def test_redact_mac_addresses(self):
        """Verify MAC addresses are redacted."""
        text = "MAC: 00:1B:44:11:3A:B7"
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "00:1B:44:11:3A:B7" not in result.text
        assert "[REDACTED]" in result.text

    def test_multi_pass_redaction(self):
        """Verify multi-pass redaction catches nested patterns."""
        # This tests that after first redaction, new patterns might emerge
        text = "password=secret123 and backup_password=secret456"
        redactor = PiiRedactor(multi_pass=True)
        result = redactor.redact(text)
        
        assert "secret123" not in result.text
        assert "secret456" not in result.text
        assert result.replacements

    def test_validation_detects_leaks(self):
        """Verify validation detects potential leaks."""
        # Create a custom redactor that should trigger validation
        redactor = PiiRedactor(strict_mode=True, patterns=["dummy::(?!)"])  # No-op pattern
        text = "email@example.com AKIAIOSFODNN7EXAMPLE"
        result = redactor.redact(text)
        
        # Validation should detect potential leaks and automatically remediate them
        assert result.validation_passed
        assert result.validation_warnings is not None
        assert len(result.validation_warnings) > 0
        assert not result.failsafe_triggered
        assert "email@example.com" not in result.text
        assert "AKIAIOSFODNN7EXAMPLE" not in result.text

    def test_validation_passes_clean_text(self):
        """Verify validation passes when text is clean."""
        text = "This is clean text with no sensitive data."
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert result.validation_passed
        assert result.validation_warnings is not None
        assert len(result.validation_warnings) == 0

    def test_failsafe_triggers_when_validation_disabled(self):
        """Failsafe should replace content when no validation passes run."""
        text = "user=admin password=SuperSecret123 email@example.com"
        redactor = PiiRedactor(
            strict_mode=True,
            patterns=["dummy::(?!)"],
            validation_passes=0,
            fail_closed=True,
            block_replacement="[BLOCKED]",
        )
        result = redactor.redact(text)

        assert not result.validation_passed
        assert result.failsafe_triggered
        assert result.text == "[BLOCKED]"
        assert "SuperSecret123" not in result.text
        assert "email@example.com" not in result.text
        assert result.validation_warnings is not None
        assert "Failsafe content replacement applied." in result.validation_warnings

    def test_disabled_redactor(self):
        """Verify disabled redactor returns original text."""
        text = "email@example.com password=secret"
        redactor = PiiRedactor(enabled=False)
        result = redactor.redact(text)
        
        assert result.text == text
        assert len(result.replacements) == 0

    def test_comprehensive_log_file_redaction(self):
        """Test redaction on realistic log file content."""
        log_content = """
2024-01-15 10:30:45 INFO Connecting to database postgresql://admin:Pa$$w0rd@db.internal.com:5432/prod
2024-01-15 10:30:46 INFO Using API key: sk-abc123def456ghi789jkl
2024-01-15 10:30:47 INFO User john.doe@company.com logged in from 10.0.1.50
2024-01-15 10:30:48 INFO JWT token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123
2024-01-15 10:30:49 ERROR AWS credentials: AKIAIOSFODNN7EXAMPLE / wJalrXUtnFEMI/K7MDENG
2024-01-15 10:30:50 INFO Phone: +1-800-555-0199, SSN: 123-45-6789
        """
        redactor = PiiRedactor()
        result = redactor.redact(log_content)
        
        # Verify all sensitive data is redacted
        assert "Pa$$w0rd" not in result.text
        assert "sk-abc123def456ghi789jkl" not in result.text
        assert "john.doe@company.com" not in result.text
        assert "AKIAIOSFODNN7EXAMPLE" not in result.text
        assert "wJalrXUtnFEMI/K7MDENG" not in result.text
        assert "123-45-6789" not in result.text
        assert "10.0.1.50" not in result.text
        
        # Verify redactions occurred
        assert len(result.replacements) > 0
        assert "[REDACTED]" in result.text

    def test_environment_variable_secrets(self):
        """Test redaction of environment variable secrets."""
        text = """
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export API_TOKEN=super_secret_token_12345678
export DATABASE_PASSWORD=MySecretPassword123
        """
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in result.text
        assert "super_secret_token_12345678" not in result.text
        assert "MySecretPassword123" not in result.text

    def test_base64_encoded_secrets(self):
        """Test redaction of base64-encoded secrets."""
        text = 'secret="dGhpc19pc19hX3NlY3JldF9rZXlfZm9yX3Rlc3Rpbmdfb25seQ=="'
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        assert "dGhpc19pc19hX3NlY3JldF9rZXlfZm9yX3Rlc3Rpbmdfb25seQ==" not in result.text
        assert "[REDACTED]" in result.text

    def test_high_entropy_tokens_redacted(self):
        """High entropy tokens resembling secrets should be masked."""
        text = "api_token=9dA7fK2LmQ0sVwXyZ1p3Rt6U8b5Nc4Hg"
        redactor = PiiRedactor()
        result = redactor.redact(text)

        assert "9dA7fK2LmQ0sVwXyZ1p3Rt6U8b5Nc4Hg" not in result.text
        assert result.replacements.get("high_entropy", 0) >= 1

    def test_multiple_pattern_types_in_one_text(self):
        """Test redacting multiple different pattern types simultaneously."""
        text = """
User email@example.com accessed server 192.168.1.1
Using JWT: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.abc
AWS Key: AKIAIOSFODNN7EXAMPLE
Credit Card: 4532-1234-5678-9010
Phone: +1-555-867-5309
        """
        redactor = PiiRedactor()
        result = redactor.redact(text)
        
        # All different types should be redacted
        assert "email@example.com" not in result.text
        assert "192.168.1.1" not in result.text
        assert "eyJhbGciOiJIUzI1NiJ9" not in result.text
        assert "AKIAIOSFODNN7EXAMPLE" not in result.text
        assert "4532-1234-5678-9010" not in result.text
        assert "+1-555-867-5309" not in result.text
        
        # Multiple pattern types should be recorded
        assert len(result.replacements) >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
