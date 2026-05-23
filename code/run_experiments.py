import numpy as np
import matplotlib.pyplot as plt
import os

# Set random seed for reproducibility
np.random.seed(42)

# Create figures directory if it doesn't exist
os.makedirs("figures", exist_ok=True)

print("Starting simulations...")

# -------------------------------------------------------------------------
# 1. REGRESSION DECISION SWEEP (HEATMAP & SUFFICIENT CONDITION)
# -------------------------------------------------------------------------
print("Running Regression Decision Sweep...")

# Grid parameters
n_points = 25
rho_xy_grid = np.linspace(-0.9, 0.9, n_points)
rho_xu_grid = np.linspace(-0.9, 0.9, n_points)
q = 0.3
gamma = 0.8  # Alignment parameter between Y and U

N_samples = 15000
advantage_grid = np.zeros((n_points, n_points))
sufficient_grid = np.zeros((n_points, n_points))

# Grid for b optimization
b_candidates = np.linspace(-3.0, 3.0, 150)

# Pre-generate standard normals
Z_X = np.random.normal(0, 1, N_samples)
Z_Y = np.random.normal(0, 1, N_samples)
Z_U = np.random.normal(0, 1, N_samples)

# We use a 2-component GMM
component = np.random.binomial(1, 0.5, N_samples)
mean_shift = np.where(component == 1, 1.0, -1.0)

for i, rho_xy in enumerate(rho_xy_grid):
    for j, rho_xu in enumerate(rho_xu_grid):
        # Generate GMM samples
        X = mean_shift + Z_X
        # Y is correlated with X
        Y = mean_shift + rho_xy * Z_X + np.sqrt(1 - rho_xy**2) * Z_Y
        # U is correlated with X and Y (alignment)
        U = mean_shift + rho_xu * Z_X + gamma * np.sqrt(1 - rho_xu**2) * Z_Y + np.sqrt(1 - gamma**2) * np.sqrt(1 - rho_xu**2) * Z_U
        
        # Center the variables for variance calculations
        X_c = X - np.mean(X)
        Y_c = Y - np.mean(Y)
        U_c = U - np.mean(U)
        
        # Vanilla OLS
        b_V = np.cov(X_c, Y_c)[0, 1] / np.var(X_c)
        R_V_opt = q * np.var(Y_c) + (1 - q) * np.mean((Y_c - b_V * X_c)**2)
        
        # Optimize strategic risk over b
        # Vectorized evaluation over b_candidates
        # b_candidates: (1, K_candidates)
        # X_c, Y_c, U_c: (N, 1)
        X_mat = X_c[:, np.newaxis]
        Y_mat = Y_c[:, np.newaxis]
        U_mat = U_c[:, np.newaxis]
        b_mat = b_candidates[np.newaxis, :]
        
        F_mat = (2 * U_mat - b_mat * X_mat) * b_mat * X_mat
        G_mat = (2 * Y_mat - b_mat * X_mat) * b_mat * X_mat
        
        # R_S(b, q) = Var(Y) - (1-q) * E[G * 1(F > 0)]
        R_S_candidates = np.var(Y_c) - (1 - q) * np.mean(G_mat * (F_mat > 0), axis=0)
        idx_opt = np.argmin(R_S_candidates)
        b_S = b_candidates[idx_opt]
        R_S_opt = R_S_candidates[idx_opt]
        
        advantage_grid[j, i] = R_V_opt - R_S_opt
        
        # Check sufficient condition for optimal b_S
        G_bS = (2 * Y_c - b_S * X_c) * b_S * X_c
        Var_bS = np.var(b_S * X_c)
        Var_bV = np.var(b_V * X_c)
        Var_diff = np.var((b_S - b_V) * X_c)
        
        LHS = 2 * np.sqrt(np.mean((U_c - Y_c)**2)) * np.sqrt(Var_bS)
        RHS = 0.5 * (np.mean(np.abs(G_bS)) - Var_bV - Var_diff)
        
        sufficient_grid[j, i] = 1.0 if LHS < RHS else 0.0

# Plot Heatmap
plt.figure(figsize=(7, 6))
plt.imshow(advantage_grid, extent=[-0.9, 0.9, -0.9, 0.9], origin='lower', cmap='coolwarm', aspect='auto')
plt.colorbar(label='Strategic Advantage $\Delta^*(E)$')
# Overlay the sufficient condition region as a contour
plt.contour(rho_xy_grid, rho_xu_grid, sufficient_grid, levels=[0.5], colors='black', linestyles='dashed', linewidths=2)
# Label the contour
plt.text(-0.8, 0.8, 'Sufficient\nCondition\nHolds', color='black', fontsize=9, fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

plt.xlabel('Correlation $(X, Y)$')
plt.ylabel('Correlation $(X, U)$')
plt.title('Regression Strategic Advantage & Sufficient Region')
plt.tight_layout()
plt.savefig("figures/regression_decision_sweep.png", dpi=300)
plt.close()

# -------------------------------------------------------------------------
# 2. CLASSIFICATION DECISION SWEEP (HEATMAP & PIECEWISE LINEAR LINES)
# -------------------------------------------------------------------------
print("Running Classification Decision Sweep...")

# Helper: softmax regression training
def train_softmax(X_train, y_train, K_classes, lr=0.3, epochs=100):
    N, d = X_train.shape
    Theta = np.zeros((K_classes, d))
    for epoch in range(epochs):
        # Compute scores
        scores = X_train @ Theta.T # (N, K)
        scores -= np.max(scores, axis=1, keepdims=True) # numeric stability
        probs = np.exp(scores) / np.sum(np.exp(scores), axis=1, keepdims=True)
        # Gradient
        grad = np.zeros_like(Theta)
        for c in range(K_classes):
            indicator = (y_train == c).astype(float)
            grad[c] = (1.0 / N) * np.sum((probs[:, c] - indicator)[:, np.newaxis] * X_train, axis=0)
        Theta -= lr * grad
    return Theta

def evaluate_softmax(X_val, y_val, Theta):
    scores = X_val @ Theta.T
    preds = np.argmax(scores, axis=1)
    return np.mean(preds != y_val)

# Generate Classification distribution
K = 3
pi = np.array([0.35, 0.4, 0.25])
mu = np.array([[-1.0, -1.0], [0.0, 1.5], [1.0, -1.0]])
sigma = np.sqrt(0.5)

def sample_classification(N, alpha_align):
    U = np.random.choice([0, 1, 2], size=N, p=pi)
    X = np.zeros((N, 2))
    Y = np.zeros(N, dtype=int)
    for i in range(N):
        u = U[i]
        X[i] = np.random.normal(mu[u], sigma)
        # Y is aligned with U with probability 1-alpha
        if np.random.rand() < (1.0 - alpha_align):
            Y[i] = u
        else:
            # Randomly select another class
            Y[i] = np.random.choice([c for c in range(K) if c != u])
    return U, X, Y

# A. Piecewise linear risk plot for fixed alpha = 0.15
print("  Generating Piecewise Linear risk curve...")
U_sim, X_sim, Y_sim = sample_classification(40000, 0.15)
# Add bias term to X
X_sim_b = np.hstack([X_sim, np.ones((len(X_sim), 1))])

# Precompute quantities for each default i
pi_est = np.zeros(K)
P_Y_neq_i = np.zeros(K)
P_Y_neq_i_given_U_neq_i = np.zeros(K)
r_minus_i = np.zeros(K)

for i in range(K):
    pi_est[i] = np.mean(U_sim == i)
    P_Y_neq_i[i] = np.mean(Y_sim != i)
    
    mask_revealed = (U_sim != i)
    X_rev = X_sim_b[mask_revealed]
    Y_rev = Y_sim[mask_revealed]
    
    P_Y_neq_i_given_U_neq_i[i] = np.mean(Y_rev != i)
    
    # Train predictor on revealed subpopulation
    Theta = train_softmax(X_rev, Y_rev, K)
    r_minus_i[i] = evaluate_softmax(X_rev, Y_rev, Theta)

# Compute curves over q
q_grid = np.linspace(0.0, 1.0, 100)
R_S_i = np.zeros((K, len(q_grid)))
for i in range(K):
    # R_i_S(q) = P(Y != i) + (1-pi_i)*(1-q)*(r^{-i}_X - P(Y != i | U != i))
    R_S_i[i] = P_Y_neq_i[i] + (1 - pi_est[i]) * (1 - q_grid) * (r_minus_i[i] - P_Y_neq_i_given_U_neq_i[i])

# Optimal strategic risk (lower envelope)
R_S_opt = np.minimum.reduce(R_S_i, axis=0)

plt.figure(figsize=(7, 5))
for i in range(K):
    plt.plot(q_grid, R_S_i[i], label=f'$R_S^{i+1}(q)$ (Default Class {i+1})', linestyle=':', alpha=0.8)
plt.plot(q_grid, R_S_opt, label='Optimal Strategic Risk $R_S^*(q)$', color='black', linewidth=2.5)
plt.xlabel('Default-Disclosure Probability $q$')
plt.ylabel('Receiver Risk')
plt.title('Piecewise-Linear Envelope of Optimal Strategic Risk')
plt.legend(frameon=True)
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig("figures/classification_piecewise_linear.png", dpi=300)
plt.close()

# B. Heatmap of strategic advantage over (q, alpha)
print("  Generating Classification Advantage Heatmap...")
alpha_grid = np.linspace(0.05, 0.75, 15)
q_grid_hm = np.linspace(0.05, 0.95, 15)
advantage_hm = np.zeros((len(alpha_grid), len(q_grid_hm)))

for a_idx, alpha_val in enumerate(alpha_grid):
    U_a, X_a, Y_a = sample_classification(20000, alpha_val)
    X_a_b = np.hstack([X_a, np.ones((len(X_a), 1))])
    
    # Train vanilla classifier on entire population
    Theta_vanilla = train_softmax(X_a_b, Y_a, K)
    r_vanilla = evaluate_softmax(X_a_b, Y_a, Theta_vanilla)
    
    # Precompute terms for defaults
    pi_a = np.zeros(K)
    P_Y_neq_i_a = np.zeros(K)
    P_Y_neq_i_given_U_neq_i_a = np.zeros(K)
    r_minus_i_a = np.zeros(K)
    
    for i in range(K):
        pi_a[i] = np.mean(U_a == i)
        P_Y_neq_i_a[i] = np.mean(Y_a != i)
        mask = (U_a != i)
        P_Y_neq_i_given_U_neq_i_a[i] = np.mean(Y_a[mask] != i)
        Theta_i = train_softmax(X_a_b[mask], Y_a[mask], K)
        r_minus_i_a[i] = evaluate_softmax(X_a_b[mask], Y_a[mask], Theta_i)
        
    for q_idx, q_val in enumerate(q_grid_hm):
        # Vanilla risk
        # R_V*(q) = min_c [q * P(Y != c) + (1-q) * r_vanilla]
        R_V_candidates = [q_val * P_Y_neq_i_a[c] + (1 - q_val) * r_vanilla for c in range(K)]
        R_V_opt_val = np.min(R_V_candidates)
        
        # Strategic risks
        R_S_vals = [P_Y_neq_i_a[i] + (1 - pi_a[i]) * (1 - q_val) * (r_minus_i_a[i] - P_Y_neq_i_given_U_neq_i_a[i]) for i in range(K)]
        R_S_opt_val = np.min(R_S_vals)
        
        advantage_hm[a_idx, q_idx] = R_V_opt_val - R_S_opt_val

plt.figure(figsize=(7, 6))
plt.imshow(advantage_hm, extent=[0.05, 0.95, 0.05, 0.75], origin='lower', cmap='plasma', aspect='auto')
plt.colorbar(label='Classification Strategic Advantage $\Delta^*(q)$')
plt.xlabel('Default-Disclosure Probability $q$')
plt.ylabel('Alignment Noise $\\alpha$')
plt.title('Classification Strategic Advantage Sweep')
plt.tight_layout()
plt.savefig("figures/classification_decision_sweep.png", dpi=300)
plt.close()


# -------------------------------------------------------------------------
# 3. OFFLINE LEARNING CURVES (EXCESS RISK VS SAMPLE SIZE)
# -------------------------------------------------------------------------
print("Running Offline Generalization Gaps...")

# Range of sample sizes
n_sizes = [50, 100, 200, 500, 1000, 2000, 4000]
M_repeats = 15

# Large test set for regression
# For regression GMM:
comp_t = np.random.binomial(1, 0.5, 20000)
shift_t = np.where(comp_t == 1, 1.0, -1.0)
X_test_reg = shift_t + np.random.normal(0, 1, 20000)
Y_test_reg = shift_t + 0.5 * np.random.normal(0, 1, 20000)
U_test_reg = shift_t + 0.5 * np.random.normal(0, 1, 20000) + 0.5 * np.random.normal(0, 1, 20000)

X_test_reg_c = X_test_reg - np.mean(X_test_reg)
Y_test_reg_c = Y_test_reg - np.mean(Y_test_reg)
U_test_reg_c = U_test_reg - np.mean(U_test_reg)

# True optimal strategic risk for regression (evaluated on test set)
b_V_test = np.cov(X_test_reg_c, Y_test_reg_c)[0, 1] / np.var(X_test_reg_c)
R_S_test_candidates = np.var(Y_test_reg_c) - (1 - q) * np.mean(((2 * Y_test_reg_c[:, np.newaxis] - b_candidates * X_test_reg_c[:, np.newaxis]) * b_candidates * X_test_reg_c[:, np.newaxis]) * (((2 * U_test_reg_c[:, np.newaxis] - b_candidates * X_test_reg_c[:, np.newaxis]) * b_candidates * X_test_reg_c[:, np.newaxis]) > 0), axis=0)
R_S_opt_reg_true = np.min(R_S_test_candidates)
b_S_true = b_candidates[np.argmin(R_S_test_candidates)]

reg_excess_means = []
reg_excess_se = []

for n in n_sizes:
    excess_runs = []
    for run in range(M_repeats):
        comp = np.random.binomial(1, 0.5, n)
        shift = np.where(comp == 1, 1.0, -1.0)
        X_tr = shift + np.random.normal(0, 1, n)
        Y_tr = shift + 0.5 * np.random.normal(0, 1, n)
        U_tr = shift + 0.5 * np.random.normal(0, 1, n) + 0.5 * np.random.normal(0, 1, n)
        
        X_tr_c = X_tr - np.mean(X_tr)
        Y_tr_c = Y_tr - np.mean(Y_tr)
        U_tr_c = U_tr - np.mean(U_tr)
        
        # Empirical ERM search
        R_S_emp = np.var(Y_tr_c) - (1 - q) * np.mean(((2 * Y_tr_c[:, np.newaxis] - b_candidates * X_tr_c[:, np.newaxis]) * b_candidates * X_tr_c[:, np.newaxis]) * (((2 * U_tr_c[:, np.newaxis] - b_candidates * X_tr_c[:, np.newaxis]) * b_candidates * X_tr_c[:, np.newaxis]) > 0), axis=0)
        b_S_emp = b_candidates[np.argmin(R_S_emp)]
        
        # Evaluate on test set
        R_S_test_emp = np.var(Y_test_reg_c) - (1 - q) * np.mean(((2 * Y_test_reg_c - b_S_emp * X_test_reg_c) * b_S_emp * X_test_reg_c) * (((2 * U_test_reg_c - b_S_emp * X_test_reg_c) * b_S_emp * X_test_reg_c) > 0))
        excess_runs.append(max(0.0, R_S_test_emp - R_S_opt_reg_true))
    
    reg_excess_means.append(np.mean(excess_runs))
    reg_excess_se.append(np.std(excess_runs) / np.sqrt(M_repeats))

plt.figure(figsize=(6, 4))
plt.errorbar(n_sizes, reg_excess_means, yerr=reg_excess_se, fmt='-o', color='blue', ecolor='lightblue', capsize=5, label='Regression')
plt.xlabel('Sample Size $n$')
plt.ylabel('Excess Risk $R_S(\\hat{b}_n) - R_S(b^*)$')
plt.title('Regression Offline Learning Curve')
plt.xscale('log')
plt.yscale('log')
plt.grid(True, which="both", linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig("figures/regression_offline_learning.png", dpi=300)
plt.close()

# Classification offline gaps
U_val, X_val, Y_val = sample_classification(20000, 0.25)
X_val_b = np.hstack([X_val, np.ones((len(X_val), 1))])

# True optimal risk for classification (approximated on validation set)
true_risks = []
Theta_opts = []
for i in range(K):
    mask = (U_val != i)
    Theta_opt_i = train_softmax(X_val_b[mask], Y_val[mask], K)
    Theta_opts.append(Theta_opt_i)
    # Using parameters from outer loop that are stable
    pi_i_val = np.mean(U_val == i)
    P_Y_neq_i_val = np.mean(Y_val != i)
    P_Y_neq_i_given_U_neq_i_val = np.mean(Y_val[mask] != i)
    true_risks.append(P_Y_neq_i_val + (1 - pi_i_val) * (1 - q) * (evaluate_softmax(X_val_b[mask], Y_val[mask], Theta_opt_i) - P_Y_neq_i_given_U_neq_i_val))
true_opt_class_risk = np.min(true_risks)

class_excess_means = []
class_excess_se = []

for n in n_sizes:
    excess_runs = []
    for run in range(M_repeats):
        U_tr, X_tr, Y_tr = sample_classification(n, 0.25)
        X_tr_b = np.hstack([X_tr, np.ones((n, 1))])
        
        # Empirical ERM
        emp_risks = []
        emp_Thetas = []
        for i in range(K):
            mask = (U_tr != i)
            if np.sum(mask) < 5:
                # Handle edge cases
                emp_Thetas.append(np.zeros((K, 3)))
                emp_risks.append(1.0)
                continue
            Theta_opt_i = train_softmax(X_tr_b[mask], Y_tr[mask], K)
            emp_Thetas.append(Theta_opt_i)
            # Evaluate empirical risk
            r_err_emp = np.mean(np.argmax(X_tr_b[mask] @ Theta_opt_i.T, axis=1) != Y_tr[mask])
            pi_emp = np.mean(U_tr == i)
            P_Y_neq_i_emp = np.mean(Y_tr != i)
            P_Y_neq_i_given_U_neq_i_emp = np.mean(Y_tr[mask] != i)
            emp_risks.append(P_Y_neq_i_emp + (1 - pi_emp) * (1 - q) * (r_err_emp - P_Y_neq_i_given_U_neq_i_emp))
            
        i_opt_emp = np.argmin(emp_risks)
        Theta_opt_emp = emp_Thetas[i_opt_emp]
        
        # Evaluate true risk of empirical ERM on test set
        mask_test = (U_val != i_opt_emp)
        r_err_val = np.mean(np.argmax(X_val_b[mask_test] @ Theta_opt_emp.T, axis=1) != Y_val[mask_test])
        pi_val = np.mean(U_val == i_opt_emp)
        P_Y_neq_i_val = np.mean(Y_val != i_opt_emp)
        P_Y_neq_i_given_U_neq_i_val = np.mean(Y_val[mask_test] != i_opt_emp)
        
        true_risk_val = P_Y_neq_i_val + (1 - pi_val) * (1 - q) * (r_err_val - P_Y_neq_i_given_U_neq_i_val)
        excess_runs.append(max(0.0, true_risk_val - true_opt_class_risk))
        
    class_excess_means.append(np.mean(excess_runs))
    class_excess_se.append(np.std(excess_runs) / np.sqrt(M_repeats))

plt.figure(figsize=(6, 4))
plt.errorbar(n_sizes, class_excess_means, yerr=class_excess_se, fmt='-o', color='purple', ecolor='thistle', capsize=5, label='Classification')
plt.xlabel('Sample Size $n$')
plt.ylabel('Excess Risk $R_S(\\hat{\Theta}_n) - R_S(\\Theta^*)$')
plt.title('Classification Offline Learning Curve')
plt.xscale('log')
plt.yscale('log')
plt.grid(True, which="both", linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig("figures/classification_offline_learning.png", dpi=300)
plt.close()


# -------------------------------------------------------------------------
# 4. ONLINE REGRET CONVERGENCE (BANDIT GD & EXP3+OGD)
# -------------------------------------------------------------------------
print("Running Online Regret Convergence...")

T_steps = 3000

# A. Regression Online Regret for d=1 and d=3
print("  Running Regression Bandit OGD...")
def generate_online_reg(T, d):
    X = np.random.normal(0, 1, (T, d))
    b_star = np.ones(d) / np.sqrt(d)
    Y = X @ b_star + np.random.normal(0, 0.5, T)
    U = Y + np.random.normal(0, 0.5, T)
    return X, Y, U, b_star

def run_bandit_ogd(X, Y, U, b_star, T, d):
    # Parameters
    delta_0 = 0.5
    eta_coef = 0.2
    b = np.zeros(d)
    
    regrets = []
    cum_regret = 0.0
    
    # Pre-evaluate optimal true strategic risk
    b_opt = b_star  # Close enough
    
    for t in range(T):
        # Decreasing exploration radius
        delta_t = delta_0 * (t + 1)**(-0.25)
        eta_t = eta_coef / (t + 1)**(0.5)
        
        # Sample random direction on sphere
        v = np.random.normal(0, 1, d)
        v /= np.linalg.norm(v)
        
        # Perturbed parameter
        b_perturbed = b + delta_t * v
        
        # Game step
        x_t = X[t]
        y_t = Y[t]
        u_t = U[t]
        
        F_t = (2 * u_t - b_perturbed @ x_t) * (b_perturbed @ x_t)
        if F_t > 0:
            # Senders reveal
            loss_t = (y_t - b_perturbed @ x_t)**2
        else:
            # Senders withhold
            loss_t = y_t**2
            
        # Unbiased gradient estimate
        g_hat = (d / delta_t) * loss_t * v
        
        # Update
        b -= eta_t * g_hat
        # Projection to ball W of radius 2.0
        if np.linalg.norm(b) > 2.0:
            b = 2.0 * b / np.linalg.norm(b)
            
        # True risk at this step (under clean current parameter b)
        F_t_clean = (2 * u_t - b @ x_t) * (b @ x_t)
        loss_clean = (y_t - b @ x_t)**2 if F_t_clean > 0 else y_t**2
        
        F_t_opt = (2 * u_t - b_opt @ x_t) * (b_opt @ x_t)
        loss_opt = (y_t - b_opt @ x_t)**2 if F_t_opt > 0 else y_t**2
        
        cum_regret += (loss_clean - loss_opt)
        regrets.append(cum_regret)
        
    return regrets

# Run for d=1 and d=3
X_1, Y_1, U_1, b_1 = generate_online_reg(T_steps, 1)
X_3, Y_3, U_3, b_3 = generate_online_reg(T_steps, 3)

regrets_d1 = run_bandit_ogd(X_1, Y_1, U_1, b_1, T_steps, 1)
regrets_d3 = run_bandit_ogd(X_3, Y_3, U_3, b_3, T_steps, 3)

plt.figure(figsize=(6, 4))
plt.plot(regrets_d1, label='Dimension $d=1$', color='darkgreen')
plt.plot(regrets_d3, label='Dimension $d=3$', color='crimson')
# Plot O(sqrt(T)) helper curve
T_axis = np.arange(1, T_steps + 1)
plt.plot(T_axis, 2.5 * np.sqrt(T_axis), label='$\mathcal{O}(\sqrt{t})$ Reference', color='gray', linestyle='--')
plt.xlabel('Time Step $t$')
plt.ylabel('Cumulative Regret')
plt.title('Regression Online Regret (Bandit Feedback)')
plt.legend(frameon=True)
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig("figures/regression_online_regret.png", dpi=300)
plt.close()


# B. Classification Online Regret for K=2 and K=3
print("  Running Classification EXP3+OGD...")

def generate_online_class(T, K_classes):
    # Setup GMM mixtures
    U = np.random.choice(range(K_classes), size=T, p=np.ones(K_classes)/K_classes)
    X = np.zeros((T, 2))
    Y = np.zeros(T, dtype=int)
    for t in range(T):
        u = U[t]
        angle = 2 * np.pi * u / K_classes
        centroid = np.array([np.cos(angle), np.sin(angle)])
        X[t] = np.random.normal(centroid, 0.4)
        if np.random.rand() < 0.8:
            Y[t] = u
        else:
            Y[t] = np.random.choice([c for c in range(K_classes) if c != u])
    return X, Y, U

def run_exp3_ogd(X, Y, U, T, K_classes):
    # Softmax parameters
    d = 2
    # EXP3 + OGD Init
    Thetas = np.zeros((K_classes, K_classes, d))  # K instances of weight matrices
    w = np.ones(K_classes) # EXP3 weights
    
    # Exploration parameters
    gamma = (K_classes * np.log(K_classes) / T)**(1.0/3.0)
    eta = 0.15 * (gamma / (K_classes * T))**0.5
    
    cum_loss = 0.0
    cum_opt_loss = 0.0
    regrets = []
    
    # Find best fixed default predictor in hindsight (oracle baseline approximation)
    best_opt_loss = float('inf')
    for test_i in range(K_classes):
        mask = (U != test_i)
        Theta_i = train_softmax(X[mask], Y[mask], K_classes, lr=0.3, epochs=40)
        tot_l = 0.0
        for t in range(T):
            if U[t] == test_i:
                tot_l += float(Y[t] != test_i)
            else:
                score = Theta_i @ X[t]
                score -= np.max(score)
                prob = np.exp(score) / np.sum(np.exp(score))
                tot_l -= np.log(prob[Y[t]])
        if tot_l < best_opt_loss:
            best_opt_loss = tot_l
    
    opt_loss_per_step = best_opt_loss / T
    
    for t in range(T):
        p = (1 - gamma) * (w / np.sum(w)) + gamma / K_classes
        i_t = np.random.choice(range(K_classes), p=p)
        
        u_t = U[t]
        x_t = X[t]
        y_t = Y[t]
        
        if u_t == i_t:
            L_t = float(y_t != i_t)
        else:
            Theta_t = Thetas[i_t]
            scores = Theta_t @ x_t
            scores -= np.max(scores)
            probs = np.exp(scores) / np.sum(np.exp(scores))
            L_t = -np.log(probs[y_t] + 1e-12)
            
            grad = np.zeros_like(Theta_t)
            for c in range(K_classes):
                indicator = float(y_t == c)
                grad[c] = (probs[c] - indicator) * x_t
                
            Thetas[i_t] -= (eta / p[i_t]) * grad
            Thetas[i_t] = np.clip(Thetas[i_t], -2.0, 2.0)
            
        L_hat_t = np.zeros(K_classes)
        L_hat_t[i_t] = L_t / p[i_t]
        w = w * np.exp(- (gamma / K_classes) * L_hat_t)
        w /= np.max(w)
        
        cum_loss += L_t
        cum_opt_loss += opt_loss_per_step
        regrets.append(cum_loss - cum_opt_loss)
        
    return regrets

# Run for K=2 and K=3
X_k2, Y_k2, U_k2 = generate_online_class(T_steps, 2)
X_k3, Y_k3, U_k3 = generate_online_class(T_steps, 3)

regrets_k2 = run_exp3_ogd(X_k2, Y_k2, U_k2, T_steps, 2)
regrets_k3 = run_exp3_ogd(X_k3, Y_k3, U_k3, T_steps, 3)

plt.figure(figsize=(6, 4))
plt.plot(regrets_k2, label='Classes $K=2$', color='navy')
plt.plot(regrets_k3, label='Classes $K=3$', color='orange')
T_axis = np.arange(1, T_steps + 1)
plt.plot(T_axis, 1.2 * T_axis**(2.0/3.0), label='$\mathcal{O}(t^{2/3})$ Reference', color='gray', linestyle='--')
plt.xlabel('Time Step $t$')
plt.ylabel('Expected Cumulative Regret')
plt.title('Classification Online Regret (EXP3 + OGD)')
plt.legend(frameon=True)
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig("figures/classification_online_regret.png", dpi=300)
plt.close()

print("All simulations complete and figures saved successfully!")
