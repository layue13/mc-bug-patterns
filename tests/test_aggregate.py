"""python3 tests/test_aggregate.py  -- checks the enclosing-method extraction heuristic."""
import importlib.util, pathlib, sys

spec = importlib.util.spec_from_file_location("aggregate", pathlib.Path(__file__).parent.parent / "scripts/aggregate.py")
agg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agg)

SRC = """\
public class Miner extends Item {
    private int x;

    public void other() {
        int a = 1;
    }

    @Override
    public InteractionResult useOn(UseOnContext ctx,
                                   Level level) {
        String s = "}{";   // braces in strings are ignored
        if (level.isClientSide) {
            return null;
        }
        level.destroyBlock(pos, true);
        return null;
    }

    public void after() { }
}
""".splitlines()

def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    return cond

a, b = agg.enclosing_block(SRC, 15)          # the destroyBlock line
ok = all([
    check("starts at the wrapped signature (line 9)", a == 9),
    check("ends at the method's closing brace (line 17)", b == 17),
    check("does not leak into the next method", b < 19),
])
a, b = agg.enclosing_block(SRC, 5)           # inside other()
ok &= check("picks the right sibling method (4..6)", (a, b) == (4, 6))
a, b = agg.enclosing_block(["x = 1;", "y = 2;"], 1)   # no method at all
ok &= check("falls back to a window when no signature", (a, b) == (1, 2))
sys.exit(0 if ok else 1)
