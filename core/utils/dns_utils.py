"""DNS resolver utilities for DKIM/SPF/DMARC verification."""
import logging

import dns.resolver
import dns.exception

logger = logging.getLogger(__name__)


class DNSVerificationResult:
    """Result of DNS verification for a domain."""
    def __init__(self, is_valid, record, required_record, error=None):
        self.is_valid = is_valid
        self.record = record
        self.required_record = required_record
        self.error = error


def check_spf(domain, spf_record=None):
    """
    Verify SPF record for domain.
    
    Args:
        domain: Domain name to check
        spf_record: Expected SPF record (optional, for validation)
    
    Returns:
        DNSVerificationResult
    """
    try:
        # Query TXT records
        records = dns.resolver.resolve(domain, 'TXT')
        
        # Look for SPF record (v=spf1)
        for record in records:
            record_str = str(record).strip('"')
            if record_str.startswith('v=spf1'):
                # If spf_record provided, check if it matches
                if spf_record and spf_record not in record_str:
                    return DNSVerificationResult(
                        is_valid=False,
                        record=record_str,
                        required_record=spf_record,
                        error="SPF record exists but doesn't match expected value"
                    )
                return DNSVerificationResult(
                    is_valid=True,
                    record=record_str,
                    required_record=spf_record or 'v=spf1 include:mail.webmail.com ~all'
                )
        
        # No SPF record found
        return DNSVerificationResult(
            is_valid=False,
            record=None,
            required_record=spf_record or 'v=spf1 include:mail.webmail.com ~all',
            error="No SPF record found"
        )
    except dns.exception.DNSException as e:
        logger.warning("DNS error checking SPF for %s: %s", domain, e)
        return DNSVerificationResult(
            is_valid=False,
            record=None,
            required_record=spf_record or 'v=spf1 include:mail.webmail.com ~all',
            error=str(e)
        )


def check_dkim(domain, selector='default', dkim_public_key=None):
    """
    Verify DKIM record for domain.
    
    Args:
        domain: Domain name to check
        selector: DKIM selector (default: 'default')
        dkim_public_key: Expected DKIM public key (optional)
    
    Returns:
        DNSVerificationResult
    """
    try:
        # Query DKIM record: {selector}._domainkey.{domain}
        dkim_domain = f"{selector}._domainkey.{domain}"
        records = dns.resolver.resolve(dkim_domain, 'TXT')
        
        for record in records:
            record_str = str(record).strip('"')
            if record_str.startswith('v=DKIM1'):
                # If dkim_public_key provided, check if it's present in record
                if dkim_public_key and dkim_public_key not in record_str:
                    return DNSVerificationResult(
                        is_valid=False,
                        record=record_str,
                        required_record=dkim_public_key,
                        error="DKIM record exists but public key doesn't match"
                    )
                return DNSVerificationResult(
                    is_valid=True,
                    record=record_str,
                    required_record=dkim_public_key or f"v=DKIM1; p={{{selector}_public_key}}"
                )
        
        return DNSVerificationResult(
            is_valid=False,
            record=None,
            required_record=dkim_public_key or f"v=DKIM1; p={{{selector}_public_key}}",
            error="No DKIM record found"
        )
    except dns.exception.DNSException as e:
        logger.warning("DNS error checking DKIM for %s: %s", domain, e)
        return DNSVerificationResult(
            is_valid=False,
            record=None,
            required_record=dkim_public_key or f"v=DKIM1; p={{{selector}_public_key}}",
            error=str(e)
        )


def check_dmarc(domain, dmarc_policy=None):
    """
    Verify DMARC record for domain.
    
    Args:
        domain: Domain name to check
        dmarc_policy: Expected DMARC policy (optional)
    
    Returns:
        DNSVerificationResult
    """
    try:
        # Query DMARC record: _dmarc.{domain}
        dmarc_domain = f"_dmarc.{domain}"
        records = dns.resolver.resolve(dmarc_domain, 'TXT')
        
        for record in records:
            record_str = str(record).strip('"')
            if record_str.startswith('v=DMARC1'):
                # If dmarc_policy provided, check if it matches
                if dmarc_policy and dmarc_policy not in record_str:
                    return DNSVerificationResult(
                        is_valid=False,
                        record=record_str,
                        required_record=dmarc_policy,
                        error="DMARC record exists but policy doesn't match"
                    )
                return DNSVerificationResult(
                    is_valid=True,
                    record=record_str,
                    required_record=dmarc_policy or "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com"
                )
        
        return DNSVerificationResult(
            is_valid=False,
            record=None,
            required_record=dmarc_policy or "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com",
            error="No DMARC record found"
        )
    except dns.exception.DNSException as e:
        logger.warning("DNS error checking DMARC for %s: %s", domain, e)
        return DNSVerificationResult(
            is_valid=False,
            record=None,
            required_record=dmarc_policy or "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com",
            error=str(e)
        )


def verify_domain_dns(domain):
    """
    Verify all DNS records (SPF, DKIM, DMARC) for a domain.
    
    Returns dict with verification results for each record type.
    """
    return {
        'spf': check_spf(domain),
        'dkim': check_dkim(domain),
        'dmarc': check_dmarc(domain)
    }

