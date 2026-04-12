import asyncio
import time
import pytest
from orchestrator import do_save_async
from core.execution.pool import PoolManager
from core.config import DATA_DIR

@pytest.fixture(scope="module")
async def real_pool():
    manager = PoolManager.get_instance()
    # Enable pooling for this test
    from core import config
    config.ENABLE_ENV_POOLING = True
    config.POOL_MAX_SIZE = 1
    
    # We use a relatively lighter "heavy" lib for integration test if possible
    # but let's stick to what's in DEFAULT_POOL_SPECS if we want to test the real deal.
    # Actually, let's use sklearn as a test case if we add it, or just torch.
    
    await manager.initialize()
    yield manager
    await manager.shutdown()

@pytest.mark.asyncio
async def test_pooled_execution_speedup(test_db, real_pool):
    # Manually trigger preparation to avoid background worker race/scheduling issues in tests
    start_prep = time.time()
    await real_pool._prepare_env("tiny-pool")
    prep_duration = time.time() - start_prep
    print(f"\n[INTEGRATION] Manual preparation took {prep_duration:.2f}s")
    
    # Wait for it to appear in the queue (should be immediate after _prepare_env)
    assert real_pool.pools["tiny-pool"].qsize() == 1
    
    code = """
import radon
from radon.complexity import cc_visit

def get_complexity(code_str):
    return cc_visit(code_str)[0].complexity
"""
    test_code = """
complexity = get_complexity("def hello(): pass")
assert complexity == 1
"""
    
    # Measure time for registration
    start_reg = time.time()
    success = await do_save_async(
        name="test_pooled_radon",
        code=code,
        test_code=test_code,
        dependencies=["radon"],
        description="Testing pooled execution speed with radon",
        project="test_system"
    )
    duration = time.time() - start_reg
    
    assert success is True
    print(f"\n[INTEGRATION] Pooled registration (tiny-pool) took {duration:.2f}s")
    assert duration < 5.0 # Tiny pool should be extremely fast
