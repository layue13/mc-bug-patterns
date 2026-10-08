class Tests {
    // ---- D3
    class BadHandler {
        // ruleid: mc-d3-handler-ignores-simulate
        public ItemStack insertItem(int slot, ItemStack stack, boolean simulate) {
            this.items[slot] = stack;
            return ItemStack.EMPTY;
        }
        // ruleid: mc-d3-handler-ignores-simulate
        public ItemStack extractItem(int slot, int amount, boolean simulate) {
            return this.items[slot].copy();
        }
    }
    class GoodHandler {
        // ok: mc-d3-handler-ignores-simulate
        public ItemStack insertItem(int slot, ItemStack stack, boolean simulate) {
            if (!simulate) { this.items[slot] = stack; }
            return ItemStack.EMPTY;
        }
    }
    // ---- D5
    class BadFluid {
        // ruleid: mc-d5-fluid-handler-ignores-action
        public int fill(FluidStack r, FluidAction action) { this.tank.add(r.getAmount()); return r.getAmount(); }
        // ruleid: mc-d5-fluid-handler-ignores-action
        public FluidStack drain(FluidStack r, boolean doDrain) { return r.copy(); }
    }
    class GoodFluid {
        // ok: mc-d5-fluid-handler-ignores-action
        public int fill(FluidStack r, FluidAction action) { if (action.execute()) { this.tank.add(r.getAmount()); } return r.getAmount(); }
    }
    // ---- D1
    class BadMenu {
        // ruleid: mc-d1-menu-always-valid
        public boolean stillValid(Player p) { return true; }
    }
    class GoodMenu {
        // ok: mc-d1-menu-always-valid
        public boolean stillValid(Player p) { return Container.stillValidBlockEntity(this.be, p); }
    }
    class SaveOnClose {
        // ruleid: mc-d1-item-backed-menu-saves-on-close-only
        public void removed(Player p) { super.removed(p); this.stack.getOrCreateTag().put("Inv", this.handler.serializeNBT()); }
    }
    // ---- D2
    class ManualMove {
        // ruleid: mc-d2-manual-quickmove
        public ItemStack quickMoveStack(Player p, int i) {
            Slot s = this.slots.get(i);
            s.set(ItemStack.EMPTY);
            this.slots.get(31).set(s.getItem());
            return ItemStack.EMPTY;
        }
    }
    class VanillaMove {
        // ok: mc-d2-manual-quickmove
        public ItemStack quickMoveStack(Player p, int i) {
            Slot s = this.slots.get(i);
            if (!this.moveItemStackTo(s.getItem(), 0, 9, false)) { return ItemStack.EMPTY; }
            s.set(ItemStack.EMPTY);
            return ItemStack.EMPTY;
        }
    }
    // ---- D4
    class BackpackItem extends Item {
        public BackpackItem(Item.Properties p) { super(p); }
        public InteractionResultHolder<ItemStack> use(Level l, Player p, InteractionHand h) {
            // ruleid: mc-d4-inventory-item-stackable
            NetworkHooks.openScreen((ServerPlayer) p, provider);
            return null;
        }
    }
    class SafeBackpackItem extends Item {
        public SafeBackpackItem() { super(new Item.Properties().stacksTo(1)); }
        public InteractionResultHolder<ItemStack> use(Level l, Player p, InteractionHand h) {
            // ok: mc-d4-inventory-item-stackable
            NetworkHooks.openScreen((ServerPlayer) p, provider);
            return null;
        }
    }
    class Capture {
        void capture(ItemStack stack, Player p, LivingEntity target) {
            CompoundTag tag = new CompoundTag();
            // ruleid: mc-d4-entity-save-to-item
            target.saveWithoutId(tag);
        }
        void captureSafe(ItemStack stack, Player p, LivingEntity target) {
            if (isBoss(target)) { return; }
            CompoundTag tag = new CompoundTag();
            // ok: mc-d4-entity-save-to-item
            target.saveWithoutId(tag);
        }
    }
    // ---- G1
    class MinerItem extends Item {
        void useOn(Level level, Player player, BlockPos pos) {
            // ruleid: mc-g1-world-edit-without-protection-check
            level.destroyBlock(pos, true);
        }
        void useOnSafe(Level level, Player player, BlockPos pos) {
            if (!level.mayInteract(player, pos)) { return; }
            // ok: mc-g1-world-edit-without-protection-check
            level.destroyBlock(pos, true);
        }
        void clientOnly(Level level, BlockPos pos) {
            if (level.isClientSide) {
                // ok: mc-g1-world-edit-without-protection-check
                level.removeBlock(pos, false);
            }
        }
    }
    class Boom {
        void a(Level w, int count) {
            // ruleid: mc-g1-unbounded-explosion-power
            w.explode(null, 0, 0, 0, count * 4.0F, true);
            // ok: mc-g1-unbounded-explosion-power
            w.explode(null, 0, 0, 0, Math.min(count * 4.0F, 10.0F), true);
            // ok: mc-g1-unbounded-explosion-power
            w.explode(null, 0, 0, 0, 4.0F, true);
        }
    }
    // ---- G2
    class Loader {
        void a(ServerLevel l) {
            // ruleid: mc-g2-forced-chunk-loading
            ForgeChunkManager.forceChunk(l, "m", pos, 0, 0, true, true);
            // ruleid: mc-g2-forced-chunk-loading
            l.setChunkForced(0, 0, true);
        }
    }
    // ---- G3
    class Weather {
        void a(ServerLevel w, Player p) {
            // ruleid: mc-g3-global-world-state-from-gameplay
            w.setDayTime(1000L);
            // ruleid: mc-g3-global-world-state-from-gameplay
            w.setRainLevel(1.0F);
            // ruleid: mc-g3-creative-like-flight
            p.getAbilities().mayfly = true;
        }
    }
    // ---- G4
    class Backdoor {
        void a(MinecraftServer s, ServerPlayer p) {
            // ruleid: mc-g4-op-grant-or-shell
            s.getPlayerList().op(p.getGameProfile());
            // ruleid: mc-g4-op-grant-or-shell
            Runtime.getRuntime().exec("sh");
        }
    }
    class Packet {
        void handle(MyMsg msg, Supplier<NetworkEvent.Context> ctx) {
            ServerPlayer sp = ctx.get().getSender();
            // ruleid: mc-g4-packet-handler-unchecked-position
            BlockEntity be = sp.level.getBlockEntity(msg.pos);
        }
        void handleSafe(MyMsg msg, Supplier<NetworkEvent.Context> ctx) {
            ServerPlayer sp = ctx.get().getSender();
            if (sp.distanceToSqr(msg.pos.getX(), msg.pos.getY(), msg.pos.getZ()) > 64) { return; }
            // ok: mc-g4-packet-handler-unchecked-position
            BlockEntity be = sp.level.getBlockEntity(msg.pos);
        }
    }
    // ---- C1
    class Recipes {
        void a(RecipeManager rm, Container c, Level l) {
            // ruleid: mc-c1-recipe-optional-get
            Recipe r = rm.getRecipeFor(TYPE, c, l).get();
            // ok: mc-c1-recipe-optional-get
            Optional<Recipe> o = rm.getRecipeFor(TYPE, c, l);
        }
    }
    class Hook {
        void a(EntityHitResult hit) {
            // ruleid: mc-c1-nullable-entity-hit
            hit.getEntity().kill();
        }
        void b(EntityHitResult hit) {
            if (hit != null) {
                // ok: mc-c1-nullable-entity-hit
                hit.getEntity().kill();
            }
        }
    }
    class Redstone {
        // ruleid: mc-c1-redstone-reentrant-action
        public void neighborChanged(BlockState s, Level w, BlockPos p, Block b, BlockPos f, boolean m) {
            w.setBlock(p, s, 3);
        }
        // ok: mc-c1-redstone-reentrant-action
        public void neighborChanged2(BlockState s, Level w, BlockPos p, Block b, BlockPos f, boolean m) {
            w.scheduleTick(p, this, 2);
        }
    }
    // ---- C2
    class Common {
        void a() {
            // ruleid: mc-c2-client-class-in-common-code
            Minecraft.getInstance().player.sendSystemMessage(null);
        }
    }
    class Egg {
        void a() {
            // ruleid: mc-c2-date-triggered-branch
            if (LocalDate.now().getMonthValue() == 4) { }
            // ruleid: mc-c2-date-triggered-branch
            if (Calendar.getInstance().get(Calendar.MONTH) == 3) { }
        }
    }
}
