/* Synapse AI - 神经元网络可视化引擎 */

class BrainViz {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.neurons = [];       // 神经元数组
        this.synapses = [];      // 突触连接数组
        this.particles = [];     // 信号粒子
        this.dataFlows = [];     // 环境数据粒子
        this.animationId = null;
        this.active = true;
        this.excitement = 0;         // 当前兴奋度 (0-1)
        this.targetExcitement = 0;   // 目标兴奋度（平滑过渡）
        this.time = 0;
        this.mouseX = -1000;  // 鼠标位置（用于交互）
        this.mouseY = -1000;

        this.resize();
        window.addEventListener('resize', () => this.resize());

        // 鼠标交互：神经元会被鼠标吸引
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            this.mouseX = e.clientX - rect.left;
            this.mouseY = e.clientY - rect.top;
        });
        this.canvas.addEventListener('mouseleave', () => {
            this.mouseX = -1000;
            this.mouseY = -1000;
        });

        this.initNeurons();  // 初始化神经元网络
        this.animate();      // 启动动画循环
    }

    /**
     * 响应画布大小变化，重新初始化网络
     */
    resize() {
        const dpr = Math.min(window.devicePixelRatio, 2);  // 限制像素比以保证性能
        this.canvas.width = this.canvas.offsetWidth * dpr;
        this.canvas.height = this.canvas.offsetHeight * dpr;
        this.width = this.canvas.offsetWidth;
        this.height = this.canvas.offsetHeight;
        this.ctx.setTransform(1, 0, 0, 1, 0, 0);
        this.ctx.scale(dpr, dpr);
        this.initNeurons();
    }

    /**
     * 初始化神经元网络
     * 采用集群分布模式，使神经元分布更自然
     */
    initNeurons() {
        const density = 18000;
        const count = Math.max(Math.floor((this.width * this.height) / density), 35);
        this.neurons = [];

        // 生成 3-5 个集群中心，神经元围绕集群分布
        const clusters = 3 + Math.floor(Math.random() * 3);
        const clusterCenters = [];
        for (let c = 0; c < clusters; c++) {
            clusterCenters.push({
                x: this.width * (0.15 + Math.random() * 0.7),
                y: this.height * (0.15 + Math.random() * 0.7),
            });
        }

        for (let i = 0; i < count; i++) {
            const cluster = clusterCenters[Math.floor(Math.random() * clusters)];
            const spreadX = (Math.random() - 0.5) * this.width * 0.7;
            const spreadY = (Math.random() - 0.5) * this.height * 0.7;

            this.neurons.push({
                x: cluster.x + spreadX * 0.5 + (Math.random() - 0.5) * 80,
                y: cluster.y + spreadY * 0.5 + (Math.random() - 0.5) * 80,
                radius: 2 + Math.random() * 3.5,           // 神经元半径
                vx: (Math.random() - 0.5) * 0.2,           // x方向速度
                vy: (Math.random() - 0.5) * 0.2,           // y方向速度
                phase: Math.random() * Math.PI * 2,         // 脉冲相位
                pulseSpeed: 0.015 + Math.random() * 0.04,   // 脉冲速度
                type: Math.random() > 0.75 ? 'hub' : 'normal',  // 枢纽/普通神经元
                hue: Math.random() > 0.5 ? 260 : 175,       // 色相（紫色/青色）
            });
        }

        // 限制神经元在画布范围内
        this.neurons.forEach(n => {
            n.x = Math.max(20, Math.min(this.width - 20, n.x));
            n.y = Math.max(20, Math.min(this.height - 20, n.y));
        });

        // 构建突触连接 — 近距离神经元之间建立连接
        this.synapses = [];
        for (let i = 0; i < this.neurons.length; i++) {
            const maxConns = this.neurons[i].type === 'hub' ? 8 : 4;  // 枢纽神经元有更多连接
            let connections = 0;
            for (let j = i + 1; j < this.neurons.length && connections < maxConns; j++) {
                const dx = this.neurons[i].x - this.neurons[j].x;
                const dy = this.neurons[i].y - this.neurons[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const maxDist = this.neurons[i].type === 'hub' || this.neurons[j].type === 'hub' ? 200 : 120;

                if (dist < maxDist) {
                    this.synapses.push({
                        from: i, to: j,
                        dist, maxDist,
                        signalPos: Math.random(),     // 信号在突触上的位置 (0-1)
                        signalSpeed: 0.0015 + Math.random() * 0.005,
                        signalDir: Math.random() > 0.5 ? 1 : -1,  // 信号方向
                        strength: 1 - dist / maxDist,  // 连接强度
                    });
                    connections++;
                }
            }
        }
    }

    /**
     * 添加一个信号粒子（从神经元A飞向神经元B的光点）
     */
    addSignalParticle(fromX, fromY, toX, toY) {
        this.particles.push({
            x: fromX, y: fromY, toX, toY,
            progress: 0,
            speed: 0.015 + Math.random() * 0.04,
            life: 1,
            hue: Math.random() > 0.5 ? 175 : 260,
        });
    }

    /**
     * 设置目标兴奋度（平滑过渡）
     */
    setExcitement(level) {
        this.targetExcitement = Math.max(0, Math.min(1, level));
    }

    /**
     * 脉冲 — AI 有活动时触发，产生一波信号粒子
     */
    pulse() {
        this.targetExcitement = 1;
        setTimeout(() => { this.targetExcitement = 0.25; }, 600);

        const count = 3 + Math.floor(Math.random() * 6);
        for (let i = 0; i < count; i++) {
            if (this.synapses.length === 0) break;
            const syn = this.synapses[Math.floor(Math.random() * this.synapses.length)];
            if (syn) {
                const from = this.neurons[syn.from];
                const to = this.neurons[syn.to];
                this.addSignalParticle(from.x, from.y, to.x, to.y);
            }
        }
    }

    /**
     * 主动画循环 — 每帧更新并绘制所有元素
     */
    animate() {
        if (!this.active) return;
        this.animationId = requestAnimationFrame(() => this.animate());
        this.time += 0.016;

        // 兴奋度平滑过渡（lerp 插值）
        const lerpSpeed = 0.06;
        this.excitement += (this.targetExcitement - this.excitement) * lerpSpeed;
        if (Math.abs(this.targetExcitement - this.excitement) < 0.0005) {
            this.excitement = this.targetExcitement;
        }

        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.width, this.height);

        // 背景径向渐变（随兴奋度变化）
        const bgGrad = ctx.createRadialGradient(
            this.width / 2, this.height / 2, 0,
            this.width / 2, this.height / 2, Math.max(this.width, this.height) * 0.7
        );
        bgGrad.addColorStop(0, `rgba(13, 13, 36, 0.3)`);
        bgGrad.addColorStop(1, `rgba(5, 5, 16, 0.6)`);
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, this.width, this.height);

        // 更新神经元位置（含鼠标交互和阻尼）
        for (const n of this.neurons) {
            n.x += n.vx;
            n.y += n.vy;
            n.phase += n.pulseSpeed;

            // 鼠标吸引效果
            const dx = n.x - this.mouseX;
            const dy = n.y - this.mouseY;
            const mouseDist = Math.sqrt(dx * dx + dy * dy);
            if (mouseDist < 120) {
                const force = (1 - mouseDist / 120) * 0.5;
                n.vx += (dx / mouseDist) * force * 0.1;
                n.vy += (dy / mouseDist) * force * 0.1;
            }

            // 速度阻尼
            n.vx *= 0.99;
            n.vy *= 0.99;

            // 边界反弹
            if (n.x < 0 || n.x > this.width) n.vx *= -1;
            if (n.y < 0 || n.y > this.height) n.vy *= -1;
            n.x = Math.max(0, Math.min(this.width, n.x));
            n.y = Math.max(0, Math.min(this.height, n.y));
        }

        const excitementBoost = this.excitement;
        const baseAlpha = 0.08 + excitementBoost * 0.35;   // 突触基础透明度
        const glowAlpha = 0.25 + excitementBoost * 0.55;    // 光晕透明度

        // ===== 绘制突触连接 =====
        for (const syn of this.synapses) {
            const from = this.neurons[syn.from];
            const to = this.neurons[syn.to];
            const alpha = syn.strength * baseAlpha;
            if (alpha < 0.02) continue;

            ctx.beginPath();
            ctx.moveTo(from.x, from.y);
            ctx.lineTo(to.x, to.y);

            const hue = from.type === 'hub' || to.type === 'hub' ? 175 : 260;
            ctx.strokeStyle = `hsla(${hue}, 70%, 65%, ${alpha})`;
            ctx.lineWidth = 0.4 + excitementBoost * 0.6;
            ctx.stroke();

            // 突触上的信号光点
            const boost = 1 + excitementBoost * 4;
            syn.signalPos += syn.signalSpeed * syn.signalDir * boost;
            if (syn.signalPos > 1 || syn.signalPos < 0) {
                syn.signalDir *= -1;
                syn.signalPos = Math.max(0, Math.min(1, syn.signalPos));
            }

            if (excitementBoost > 0.15) {
                const sx = from.x + (to.x - from.x) * syn.signalPos;
                const sy = from.y + (to.y - from.y) * syn.signalPos;

                ctx.beginPath();
                ctx.arc(sx, sy, 1.8, 0, Math.PI * 2);
                ctx.fillStyle = `hsla(${hue}, 80%, 70%, ${glowAlpha})`;
                ctx.fill();

                // 信号光晕
                ctx.beginPath();
                ctx.arc(sx, sy, 4, 0, Math.PI * 2);
                ctx.fillStyle = `hsla(${hue}, 80%, 70%, ${glowAlpha * 0.3})`;
                ctx.fill();
            }
        }

        // ===== 绘制信号粒子（脉冲爆发） =====
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            p.progress += p.speed;
            p.life -= 0.008;

            if (p.progress >= 1 || p.life <= 0) {
                this.particles.splice(i, 1);
                continue;
            }

            const px = p.x + (p.toX - p.x) * p.progress;
            const py = p.y + (p.toY - p.y) * p.progress;
            const alpha = p.life;

            // 径向渐变光晕
            ctx.beginPath();
            ctx.arc(px, py, 4 * alpha, 0, Math.PI * 2);
            const grad = ctx.createRadialGradient(px, py, 0, px, py, 6 * alpha);
            grad.addColorStop(0, `hsla(${p.hue}, 90%, 70%, ${alpha})`);
            grad.addColorStop(1, `hsla(${p.hue}, 90%, 70%, 0)`);
            ctx.fillStyle = grad;
            ctx.fill();
        }

        // ===== 绘制神经元 =====
        for (const n of this.neurons) {
            const pulse = Math.sin(n.phase) * 0.25 + 0.75;
            const r = n.radius * (1 + excitementBoost * 0.4 * pulse);
            const hue = n.hue;
            const isHub = n.type === 'hub';

            // 外层光晕
            const outerGlow = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, r * (isHub ? 4 : 3));
            outerGlow.addColorStop(0, `hsla(${hue}, 80%, 60%, ${glowAlpha})`);
            outerGlow.addColorStop(0.4, `hsla(${hue}, 80%, 60%, ${glowAlpha * 0.25})`);
            outerGlow.addColorStop(1, 'hsla(260, 80%, 60%, 0)');
            ctx.beginPath();
            ctx.arc(n.x, n.y, r * (isHub ? 4 : 3), 0, Math.PI * 2);
            ctx.fillStyle = outerGlow;
            ctx.fill();

            // 核心球体（径向渐变）
            ctx.beginPath();
            ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
            const coreGrad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, r);
            if (isHub) {
                coreGrad.addColorStop(0, `hsla(${hue}, 90%, 80%, ${0.7 + excitementBoost * 0.3})`);
                coreGrad.addColorStop(1, `hsla(${hue}, 80%, 50%, ${0.6 + excitementBoost * 0.4})`);
            } else {
                coreGrad.addColorStop(0, `hsla(${hue}, 80%, 75%, ${0.5 + excitementBoost * 0.5})`);
                coreGrad.addColorStop(1, `hsla(${hue}, 70%, 50%, ${0.45 + excitementBoost * 0.45})`);
            }
            ctx.fillStyle = coreGrad;
            ctx.fill();

            // 中心亮斑（高兴奋度时更亮）
            if (excitementBoost > 0.3 || isHub) {
                ctx.beginPath();
                ctx.arc(n.x, n.y, r * 0.35, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(255, 255, 255, ${0.3 + excitementBoost * 0.5})`;
                ctx.fill();
            }
        }

        // ===== 环境漂浮数据粒子 =====
        if (this.time % 3 < 0.05 && excitementBoost > 0.2) {
            const x = Math.random() * this.width;
            const y = Math.random() * this.height;
            this.dataFlows.push({ x, y, life: 1, size: 1 + Math.random() * 2 });
        }

        for (let i = this.dataFlows.length - 1; i >= 0; i--) {
            const df = this.dataFlows[i];
            df.y -= 0.3;
            df.life -= 0.01;
            if (df.life <= 0) { this.dataFlows.splice(i, 1); continue; }

            ctx.beginPath();
            ctx.arc(df.x, df.y, df.size * df.life, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(260, 80%, 70%, ${df.life * 0.5})`;
            ctx.fill();
        }
        if (this.dataFlows.length > 30) this.dataFlows.splice(0, 10);
    }

    destroy() {
        this.active = false;
        if (this.animationId) cancelAnimationFrame(this.animationId);
    }
}

// 全局实例
let brainViz = null;
