"""High-level domain verification: generates DKIM keypair, validates SPF/DKIM/DMARC."""
import dns.exception
import dns.resolver
from django.utils import timezone


def _lookup_txt(host: str) -> list[str]:
    """Return all TXT record values published at *host*, or [] if none resolve."""
    try:
        answers = dns.resolver.resolve(host, 'TXT')
    except (
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
    ):
        return []
    return [b''.join(rdata.strings).decode('utf-8', errors='ignore') for rdata in answers]


def verify_spf(domain) -> bool:
    return any(txt.startswith('v=spf1') for txt in _lookup_txt(domain.domain))


def verify_dkim(domain) -> bool:
    if not domain.dkim_public_key:
        return False
    host = f'{domain.dkim_selector}._domainkey.{domain.domain}'
    return any(txt.startswith('v=DKIM1') for txt in _lookup_txt(host))


def verify_dmarc(domain) -> bool:
    host = f'_dmarc.{domain.domain}'
    return any(txt.startswith('v=DMARC1') for txt in _lookup_txt(host))


def verify_domain(domain) -> dict:
    """Run SPF/DKIM/DMARC DNS checks for *domain*, persist the result, and return a summary."""
    spf_ok = verify_spf(domain)
    dkim_ok = verify_dkim(domain)
    dmarc_ok = verify_dmarc(domain)

    domain.spf_verified = spf_ok
    domain.dkim_verified = dkim_ok
    domain.dmarc_verified = dmarc_ok
    domain.last_checked_at = timezone.now()

    if spf_ok and dkim_ok and dmarc_ok:
        domain.verification_status = 'verified'
        if not domain.verified_at:
            domain.verified_at = timezone.now()
    elif spf_ok or dkim_ok or dmarc_ok:
        domain.verification_status = 'pending'
    else:
        domain.verification_status = 'failed'

    domain.save(update_fields=[
        'spf_verified', 'dkim_verified', 'dmarc_verified',
        'last_checked_at', 'verification_status', 'verified_at',
    ])
    return {'spf': spf_ok, 'dkim': dkim_ok, 'dmarc': dmarc_ok, 'status': domain.verification_status}
