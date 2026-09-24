from . import models


def post_init_hook(env):
    """
    Called after module installation.
    Triggers sanitization immediately if in staging environment.
    """
    import logging
    _logger = logging.getLogger(__name__)

    _logger.info("=" * 60)
    _logger.info("STAGING_DB_SANITIZER: POST-INSTALL HOOK")
    _logger.info("=" * 60)

    try:
        # Get the sanitizer model and run the check
        sanitizer_model = env['staging.database.sanitizer']
        sanitizer_model.run_sanitization_check()

        _logger.info("=" * 60)
        _logger.info("POST-INSTALL HOOK COMPLETED")
        _logger.info("=" * 60)
    except Exception as e:
        _logger.error(f"✗ Error in post-install hook: {e}")
        import traceback
        _logger.error(traceback.format_exc())