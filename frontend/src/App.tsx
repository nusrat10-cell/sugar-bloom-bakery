import { FormEvent, useEffect, useState } from "react";
import { AuthProvider, apiRequest, getAccessToken, useAuth } from "./AuthContext";

interface Product {
  id: string;
  name: string;
  description: string;
  category: string;
  price: number;
  stock: number;
  owner_id: string;
  group_id: string | null;
  assigned_to: string | null;
}

interface GroupMember {
  id: string;
  user_id: string;
  can_create: boolean;
  can_update: boolean;
  can_assign: boolean;
}

interface Group {
  id: string;
  name: string;
  description: string;
  owner_id: string;
  members: GroupMember[];
}

interface SessionInfo {
  id: string;
  ip_address: string | null;
  user_agent: string | null;
  revoked: boolean;
  created_at: string;
}

interface AdminUser {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: "user" | "admin";
  is_banned: boolean;
  ban_reason: string | null;
}

interface ActivityLog {
  id: string;
  action: string;
  actor_email: string | null;
  target_type: string | null;
  details: string | null;
  ip_address: string | null;
  created_at: string;
}

function AuthScreen() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup(email, username, fullName, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 420, margin: "48px auto", fontFamily: "sans-serif" }}>
      <h2>Sugar Bloom Bakery</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button type="button" onClick={() => { setMode("login"); setError(null); }}>
          Login
        </button>
        <button type="button" onClick={() => { setMode("signup"); setError(null); }}>
          Create Account
        </button>
      </div>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {mode === "signup" && (
          <>
            <input
              placeholder="Full Name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
            <input
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </>
        )}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password (min 8 chars)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit" disabled={submitting}>
          {submitting ? "Please wait..." : mode === "login" ? "Sign In" : "Sign Up"}
        </button>
      </form>
    </div>
  );
}

function AdminPanel({ onRefreshMain }: { onRefreshMain: () => void }) {
  const [tab, setTab] = useState<"overview" | "users" | "moderation" | "logs" | "security">("overview");
  const [overview, setOverview] = useState<Record<string, number> | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [security, setSecurity] = useState<{ recent_sessions: SessionInfo[]; failed_logins: ActivityLog[] } | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [adminStatus, setAdminStatus] = useState<string | null>(null);

  const loadTab = async (targetTab = tab) => {
    setError(null);
    try {
      if (targetTab === "overview") {
        setOverview(await apiRequest("/api/admin/overview"));
      } else if (targetTab === "users") {
        setUsers(await apiRequest(`/api/admin/users?search=${encodeURIComponent(search)}`));
      } else if (targetTab === "moderation") {
        setProducts(await apiRequest("/api/admin/products"));
      } else if (targetTab === "logs") {
        setLogs(await apiRequest("/api/admin/logs?limit=100"));
      } else if (targetTab === "security") {
        setSecurity(await apiRequest("/api/admin/security"));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load admin data");
    }
  };

  useEffect(() => {
    loadTab(tab);
  }, [tab]);

  const handleToggleBan = async (targetUser: AdminUser) => {
    setError(null);
    setAdminStatus(null);
    try {
      const nextBanned = !targetUser.is_banned;
      const reason = nextBanned ? window.prompt("Ban reason (optional):") || "" : "";
      await apiRequest(`/api/admin/users/${targetUser.id}/ban`, {
        method: "PATCH",
        body: JSON.stringify({ banned: nextBanned, reason }),
      });
      setAdminStatus(nextBanned ? `Banned ${targetUser.email}` : `Unbanned ${targetUser.email}`);
      await loadTab("users");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update ban status");
    }
  };

  const downloadCsv = async (path: string, filename: string) => {
    const token = getAccessToken();
    const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
    const res = await fetch(`${baseUrl}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: "include",
    });
    if (!res.ok) {
      setError("CSV export failed");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section style={{ marginTop: 28, padding: 16, border: "1px solid #ccc" }}>
      <h3>Admin Dashboard</h3>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
        <button type="button" onClick={() => setTab("overview")}>Overview</button>
        <button type="button" onClick={() => setTab("users")}>Users</button>
        <button type="button" onClick={() => setTab("moderation")}>Moderation</button>
        <button type="button" onClick={() => setTab("logs")}>Activity Logs</button>
        <button type="button" onClick={() => setTab("security")}>Security</button>
        <button type="button" onClick={() => downloadCsv("/api/admin/export/products.csv", "bakery_products.csv")}>
          Export Items CSV
        </button>
        <button type="button" onClick={() => downloadCsv("/api/admin/export/logs.csv", "activity_logs.csv")}>
          Export Logs CSV
        </button>
      </div>

      {adminStatus && <p style={{ color: "seagreen" }}>{adminStatus}</p>}
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {tab === "overview" && overview && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          <div><strong>Total Users:</strong> {overview.total_users}</div>
          <div><strong>Admins:</strong> {overview.admin_users}</div>
          <div><strong>Banned:</strong> {overview.banned_users}</div>
          <div><strong>Total Items:</strong> {overview.total_products}</div>
          <div><strong>Inventory Value:</strong> ${overview.total_inventory_value}</div>
          <div><strong>Groups:</strong> {overview.total_groups}</div>
          <div><strong>Activity Logs:</strong> {overview.total_activity_logs}</div>
          <div><strong>Failed Logins:</strong> {overview.failed_login_attempts}</div>
        </div>
      )}

      {tab === "users" && (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
            <input placeholder="Search email/username/name" value={search} onChange={(e) => setSearch(e.target.value)} />
            <button type="button" onClick={() => loadTab("users")}>Search</button>
          </div>
          <table border={1} cellPadding={6} style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th>Email</th>
                <th>Username</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.username}</td>
                  <td>{u.role}</td>
                  <td>{u.is_banned ? `Banned (${u.ban_reason || "no reason"})` : "Active"}</td>
                  <td style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <button
                      type="button"
                      onClick={async () => {
                        setError(null);
                        try {
                          const nextRole = u.role === "admin" ? "user" : "admin";
                          await apiRequest(`/api/admin/users/${u.id}/role`, {
                            method: "PATCH",
                            body: JSON.stringify({ role: nextRole }),
                          });
                          setAdminStatus(`Updated role for ${u.email} to ${nextRole}`);
                          await loadTab("users");
                        } catch (err) {
                          setError(err instanceof Error ? err.message : "Failed to update role");
                        }
                      }}
                    >
                      Make {u.role === "admin" ? "User" : "Admin"}
                    </button>
                    <button type="button" onClick={() => handleToggleBan(u)}>
                      {u.is_banned ? "Unban User" : "Ban User"}
                    </button>
                    <button
                      type="button"
                      onClick={async () => {
                        setError(null);
                        try {
                          await apiRequest(`/api/admin/users/${u.id}`, { method: "DELETE" });
                          setAdminStatus(`Deleted ${u.email}`);
                          await loadTab("users");
                          onRefreshMain();
                        } catch (err) {
                          setError(err instanceof Error ? err.message : "Failed to delete user");
                        }
                      }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "moderation" && (
        <table border={1} cellPadding={6} style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th>Item</th>
              <th>Category</th>
              <th>Price</th>
              <th>Stock</th>
              <th>Owner ID</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.id}>
                <td>{p.name}</td>
                <td>{p.category}</td>
                <td>${p.price}</td>
                <td>{p.stock}</td>
                <td>{p.owner_id}</td>
                <td>
                  <button
                    type="button"
                    onClick={async () => {
                      await apiRequest(`/api/admin/products/${p.id}`, { method: "DELETE" });
                      loadTab("moderation");
                      onRefreshMain();
                    }}
                  >
                    Remove Item
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {tab === "logs" && (
        <table border={1} cellPadding={6} style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>Actor</th>
              <th>Details</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id}>
                <td>{new Date(l.created_at).toLocaleString()}</td>
                <td>{l.action}</td>
                <td>{l.actor_email || "-"}</td>
                <td>{l.details || "-"}</td>
                <td>{l.ip_address || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {tab === "security" && security && (
        <div>
          <h4>Failed Login Attempts ({security.failed_logins.length})</h4>
          <ul>
            {security.failed_logins.map((f) => (
              <li key={f.id}>
                {new Date(f.created_at).toLocaleString()} — {f.actor_email || "unknown"} ({f.details}) from {f.ip_address}
              </li>
            ))}
          </ul>
          <h4>Recent Refresh Sessions ({security.recent_sessions.length})</h4>
          <ul>
            {security.recent_sessions.map((s) => (
              <li key={s.id}>
                Session {s.id.slice(0, 8)} — {s.revoked ? "Revoked" : "Active"} — IP: {s.ip_address || "unknown"}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Dashboard() {
  const { user, logout, refreshUser } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [scope, setScope] = useState<"all" | "mine">("all");
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Product form state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [price, setPrice] = useState("");
  const [stock, setStock] = useState("");
  const [selectedGroupId, setSelectedGroupId] = useState("");

  // Group & member permission form state
  const [newGroupName, setNewGroupName] = useState("");
  const [memberGroupId, setMemberGroupId] = useState("");
  const [memberUserId, setMemberUserId] = useState("");
  const [canCreate, setCanCreate] = useState(true);
  const [canUpdate, setCanUpdate] = useState(false);
  const [canAssign, setCanAssign] = useState(false);

  // Profile & password state
  const [fullNameInput, setFullNameInput] = useState(user?.full_name || "");
  const [usernameInput, setUsernameInput] = useState(user?.username || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const loadAll = async (currentScope = scope) => {
    setErrorMsg(null);
    try {
      const [prods, grps, sess] = await Promise.all([
        apiRequest<Product[]>(`/api/products?scope=${currentScope}`),
        apiRequest<Group[]>("/api/groups"),
        apiRequest<SessionInfo[]>("/api/auth/sessions"),
      ]);
      setProducts(prods);
      setGroups(grps);
      setSessions(sess);
      if (grps.length > 0 && !memberGroupId) {
        setMemberGroupId(grps[0].id);
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load data");
    }
  };

  useEffect(() => {
    loadAll(scope);
  }, [scope]);

  useEffect(() => {
    if (user) {
      setFullNameInput(user.full_name);
      setUsernameInput(user.username);
    }
  }, [user]);

  const handleSaveProduct = async (e: FormEvent) => {
    e.preventDefault();
    setStatusMsg(null);
    setErrorMsg(null);
    try {
      if (editingId) {
        await apiRequest(`/api/products/${editingId}`, {
          method: "PATCH",
          body: JSON.stringify({
            name,
            description,
            category,
            price: Number(price),
            stock: Number(stock),
          }),
        });
        setStatusMsg("Item updated");
      } else {
        await apiRequest("/api/products", {
          method: "POST",
          body: JSON.stringify({
            name,
            description,
            category,
            price: Number(price),
            stock: Number(stock),
            group_id: selectedGroupId || null,
          }),
        });
        setStatusMsg("Item created");
      }
      setEditingId(null);
      setName("");
      setDescription("");
      setCategory("");
      setPrice("");
      setStock("");
      setSelectedGroupId("");
      loadAll();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to save item");
    }
  };

  const handleDeleteProduct = async (id: string) => {
    setStatusMsg(null);
    setErrorMsg(null);
    try {
      await apiRequest(`/api/products/${id}`, { method: "DELETE" });
      setStatusMsg("Item deleted");
      loadAll();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to delete item");
    }
  };

  const handleCreateGroup = async (e: FormEvent) => {
    e.preventDefault();
    if (!newGroupName.trim()) return;
    setStatusMsg(null);
    setErrorMsg(null);
    try {
      const created = await apiRequest<Group>("/api/groups", {
        method: "POST",
        body: JSON.stringify({ name: newGroupName.trim(), description: "" }),
      });
      setNewGroupName("");
      setMemberGroupId(created.id);
      setStatusMsg("Group created");
      loadAll();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to create group");
    }
  };

  const handleAddMember = async (e: FormEvent) => {
    e.preventDefault();
    if (!memberGroupId || !memberUserId.trim()) return;
    setStatusMsg(null);
    setErrorMsg(null);
    try {
      await apiRequest(`/api/groups/${memberGroupId}/members`, {
        method: "POST",
        body: JSON.stringify({
          user_id: memberUserId.trim(),
          can_create: canCreate,
          can_update: canUpdate,
          can_assign: canAssign,
        }),
      });
      setMemberUserId("");
      setStatusMsg("Member permissions saved");
      loadAll();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to update member");
    }
  };

  const handleProfileSave = async (e: FormEvent) => {
    e.preventDefault();
    setStatusMsg(null);
    setErrorMsg(null);
    try {
      await apiRequest("/api/auth/profile", {
        method: "PATCH",
        body: JSON.stringify({ full_name: fullNameInput, username: usernameInput }),
      });
      await refreshUser();
      setStatusMsg("Profile updated");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to update profile");
    }
  };

  const handlePasswordChange = async (e: FormEvent) => {
    e.preventDefault();
    setStatusMsg(null);
    setErrorMsg(null);
    try {
      await apiRequest("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      setCurrentPassword("");
      setNewPassword("");
      await logout();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to change password");
    }
  };

  return (
    <div style={{ maxWidth: 960, margin: "24px auto", fontFamily: "sans-serif", padding: "0 16px" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2>Sugar Bloom Bakery</h2>
          <p style={{ margin: 0 }}>
            Signed in as <strong>{user?.full_name}</strong> ({user?.username}) — Role: <strong>{user?.role}</strong>
          </p>
        </div>
        <button type="button" onClick={logout}>Logout</button>
      </header>

      {statusMsg && <p style={{ color: "seagreen" }}>{statusMsg}</p>}
      {errorMsg && <p style={{ color: "crimson" }}>{errorMsg}</p>}

      <div style={{ display: "flex", gap: 8, margin: "16px 0" }}>
        <button type="button" onClick={() => setScope("all")}>All Accessible Items</button>
        <button type="button" onClick={() => setScope("mine")}>My Items Only</button>
      </div>

      <form onSubmit={handleSaveProduct} style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        <input
          placeholder="Item name (e.g. Red Velvet Cake)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          placeholder="Category (e.g. Cakes)"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          required
        />
        <input
          type="number"
          step="0.01"
          placeholder="Price (e.g. 500)"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          required
        />
        <input
          type="number"
          placeholder="Stock (e.g. 10)"
          value={stock}
          onChange={(e) => setStock(e.target.value)}
          required
        />
        <input
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        {!editingId && (
          <select value={selectedGroupId} onChange={(e) => setSelectedGroupId(e.target.value)}>
            <option value="">Personal Item (No Group)</option>
            {groups.map((g) => (
              <option key={g.id} value={g.id}>Group: {g.name}</option>
            ))}
          </select>
        )}
        <button type="submit">{editingId ? "Update Item" : "Add Item"}</button>
        {editingId && (
          <button
            type="button"
            onClick={() => {
              setEditingId(null);
              setName("");
              setCategory("");
              setPrice("");
              setStock("");
              setDescription("");
            }}
          >
            Cancel
          </button>
        )}
      </form>

      <table border={1} cellPadding={6} style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th>Name</th>
            <th>Category</th>
            <th>Price</th>
            <th>Stock</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {products.map((p) => (
            <tr key={p.id}>
              <td>{p.name}</td>
              <td>{p.category}</td>
              <td>${p.price}</td>
              <td>{p.stock}</td>
              <td style={{ display: "flex", gap: 6 }}>
                <button
                  type="button"
                  onClick={() => {
                    setEditingId(p.id);
                    setName(p.name);
                    setCategory(p.category);
                    setPrice(String(p.price));
                    setStock(String(p.stock));
                    setDescription(p.description || "");
                  }}
                >
                  Edit
                </button>
                <button type="button" onClick={() => handleDeleteProduct(p.id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <section style={{ marginTop: 24, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div>
          <h3>Groups & Member Permissions</h3>
          <form onSubmit={handleCreateGroup} style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <input
              placeholder="New group name"
              value={newGroupName}
              onChange={(e) => setNewGroupName(e.target.value)}
            />
            <button type="submit">Create Group</button>
          </form>

          <form onSubmit={handleAddMember} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <select value={memberGroupId} onChange={(e) => setMemberGroupId(e.target.value)}>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>{g.name}</option>
              ))}
            </select>
            <input
              placeholder="Member User ID (UUID)"
              value={memberUserId}
              onChange={(e) => setMemberUserId(e.target.value)}
            />
            <label>
              <input type="checkbox" checked={canCreate} onChange={(e) => setCanCreate(e.target.checked)} /> Can Create
            </label>
            <label>
              <input type="checkbox" checked={canUpdate} onChange={(e) => setCanUpdate(e.target.checked)} /> Can Update
            </label>
            <label>
              <input type="checkbox" checked={canAssign} onChange={(e) => setCanAssign(e.target.checked)} /> Can Assign
            </label>
            <button type="submit">Assign Member Permissions</button>
          </form>
        </div>

        <div>
          <h3>Profile, Password & Sessions</h3>
          <form onSubmit={handleProfileSave} style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
            <input
              placeholder="Full Name"
              value={fullNameInput}
              onChange={(e) => setFullNameInput(e.target.value)}
              required
            />
            <input
              placeholder="Username"
              value={usernameInput}
              onChange={(e) => setUsernameInput(e.target.value)}
              required
            />
            <button type="submit">Save Profile</button>
          </form>

          <form onSubmit={handlePasswordChange} style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
            <input
              type="password"
              placeholder="Current Password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="New Password (min 8 chars)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
            <button type="submit">Change Password</button>
          </form>

          <h4>Active Sessions ({sessions.length})</h4>
          <ul>
            {sessions.map((s) => (
              <li key={s.id}>
                {s.ip_address || "unknown"} — {s.revoked ? "Revoked" : "Active"}{" "}
                {!s.revoked && (
                  <button
                    type="button"
                    onClick={async () => {
                      const res = await apiRequest<{ ok: boolean; is_current_session?: boolean }>(
                        `/api/auth/sessions/${s.id}`,
                        { method: "DELETE" }
                      );
                      if (res.is_current_session) {
                        await logout();
                      } else {
                        loadAll();
                      }
                    }}
                  >
                    Revoke
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {user?.role === "admin" && <AdminPanel onRefreshMain={() => loadAll()} />}
    </div>
  );
}

function AppContent() {
  const { user, loading } = useAuth();
  if (loading) return <p style={{ padding: 24 }}>Loading...</p>;
  return user ? <Dashboard /> : <AuthScreen />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}