import React, { useEffect, useState } from "react";

interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  stock: number;
  category: string;
}

export default function App() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Form state for Create / Update
  const [showForm, setShowForm] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [name, setName] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [price, setPrice] = useState<string>("");
  const [stock, setStock] = useState<string>("");
  const [category, setCategory] = useState<string>("");

  // Single Product view state
  const [singleProduct, setSingleProduct] = useState<Product | null>(null);

  // Fetch all products (Read List)
  const fetchProducts = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/products");
      if (!res.ok) throw new Error("Failed to fetch products");
      const data = await res.json();
      setProducts(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  // Handle Create or Update submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const productData = {
      name,
      description,
      price: parseFloat(price),
      stock: parseInt(stock, 10),
      category,
    };

    try {
      if (editingId !== null) {
        // Update
        const res = await fetch(`/api/products/${editingId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(productData),
        });
        if (!res.ok) throw new Error("Failed to update product");
      } else {
        // Create
        const res = await fetch("/api/products", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(productData),
        });
        if (!res.ok) throw new Error("Failed to create product");
      }

      resetForm();
      fetchProducts();
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Open form for editing
  const handleEdit = (prod: Product) => {
    setEditingId(prod.id);
    setName(prod.name);
    setDescription(prod.description);
    setPrice(prod.price.toString());
    setStock(prod.stock.toString());
    setCategory(prod.category);
    setShowForm(true);
  };

  // Delete product
  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this bakery product?")) return;
    try {
      const res = await fetch(`/api/products/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete product");
      fetchProducts();
      if (singleProduct?.id === id) setSingleProduct(null);
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Read Single product detail
  const handleViewDetails = async (id: number) => {
    try {
      const res = await fetch(`/api/products/${id}`);
      if (!res.ok) throw new Error("Failed to fetch product details");
      const data = await res.json();
      setSingleProduct(data);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const resetForm = () => {
    setShowForm(false);
    setEditingId(null);
    setName("");
    setDescription("");
    setPrice("");
    setStock("");
    setCategory("");
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <h1 style={styles.title}>🥖 Sugar Bloom Bakery</h1>
        <p style={styles.subtitle}>Product Management Dashboard </p>
      </header>

      {error && <div style={styles.errorBanner}>{error}</div>}

      {/* Action Toolbar */}
      <div style={styles.toolbar}>
        <button
          style={styles.primaryBtn}
          onClick={() => {
            resetForm();
            setShowForm(true);
          }}
        >
          + Add New Product
        </button>
        <button style={styles.secondaryBtn} onClick={fetchProducts}>
          Refresh Catalog
        </button>
      </div>

      {/* Create / Edit Modal Form */}
      {showForm && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalContent}>
            <h2>{editingId !== null ? "Edit Product" : "Add New Bakery Product"}</h2>
            <form onSubmit={handleSubmit} style={styles.form}>
              <div style={styles.formGroup}>
                <label>Product Name:</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  style={styles.input}
                />
              </div>
              <div style={styles.formGroup}>
                <label>Description:</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                  style={styles.textarea}
                />
              </div>
              <div style={styles.formGroup}>
                <label>Price ($):</label>
                <input
                  type="number"
                  step="0.01"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  required
                  style={styles.input}
                />
              </div>
              <div style={styles.formGroup}>
                <label>Stock Quantity:</label>
                <input
                  type="number"
                  value={stock}
                  onChange={(e) => setStock(e.target.value)}
                  required
                  style={styles.input}
                />
              </div>
              <div style={styles.formGroup}>
                <label>Category:</label>
                <input
                  type="text"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  required
                  style={styles.input}
                />
              </div>
              <div style={styles.modalActions}>
                <button type="submit" style={styles.saveBtn}>
                  {editingId !== null ? "Update Product" : "Save Product"}
                </button>
                <button type="button" onClick={resetForm} style={styles.cancelBtn}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Main Content Layout */}
      <div style={styles.mainLayout}>
        {/* Product List Table */}
        <div style={styles.tableContainer}>
          <h2>Product Inventory ({products.length})</h2>
          {loading ? (
            <p>Loading products...</p>
          ) : products.length === 0 ? (
            <p>No products found.</p>
          ) : (
            <table style={styles.table}>
              <thead>
                <tr style={styles.tableHeader}>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Category</th>
                  <th>Price</th>
                  <th>Stock</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id} style={styles.tableRow}>
                    <td>{p.id}</td>
                    <td style={styles.boldText}>{p.name}</td>
                    <td>
                      <span style={styles.badge}>{p.category}</span>
                    </td>
                    <td>${p.price.toFixed(2)}</td>
                    <td>{p.stock}</td>
                    <td>
                      <button
                        style={styles.actionBtn}
                        onClick={() => handleViewDetails(p.id)}
                      >
                        View
                      </button>
                      <button
                        style={styles.editBtn}
                        onClick={() => handleEdit(p)}
                      >
                        Edit
                      </button>
                      <button
                        style={styles.deleteBtn}
                        onClick={() => handleDelete(p.id)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Single Product Inspector / Card */}
        {singleProduct && (
          <div style={styles.card}>
            <h3>🔍 Product Details (Read Single)</h3>
            <p><strong>ID:</strong> {singleProduct.id}</p>
            <p><strong>Name:</strong> {singleProduct.name}</p>
            <p><strong>Category:</strong> {singleProduct.category}</p>
            <p><strong>Description:</strong> {singleProduct.description}</p>
            <p><strong>Price:</strong> ${singleProduct.price.toFixed(2)}</p>
            <p><strong>Stock:</strong> {singleProduct.stock} units</p>
            <button
              style={styles.closeCardBtn}
              onClick={() => setSingleProduct(null)}
            >
              Close Details
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// Inline Styles for a polished professional look
const styles: { [key: string]: React.CSSProperties } = {
  container: {
    maxWidth: "1200px",
    margin: "0 auto",
    padding: "30px 20px",
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    color: "#333",
    backgroundColor: "#fdfbf7",
    minHeight: "100vh",
  },
  header: {
    textAlign: "center",
    marginBottom: "30px",
    borderBottom: "2px solid #e2d9c8",
    paddingBottom: "15px",
  },
  title: {
    margin: "0",
    color: "#5c4033",
    fontSize: "2.5rem",
  },
  subtitle: {
    margin: "5px 0 0 0",
    color: "#8c6d62",
    fontSize: "1.1rem",
  },
  errorBanner: {
    backgroundColor: "#f8d7da",
    color: "#721c24",
    padding: "12px",
    borderRadius: "6px",
    marginBottom: "20px",
    textAlign: "center",
  },
  toolbar: {
    display: "flex",
    gap: "15px",
    marginBottom: "25px",
  },
  primaryBtn: {
    backgroundColor: "#8b5a2b",
    color: "#fff",
    border: "none",
    padding: "10px 20px",
    borderRadius: "6px",
    cursor: "pointer",
    fontWeight: "bold",
    fontSize: "1rem",
  },
  secondaryBtn: {
    backgroundColor: "#d7ccc8",
    color: "#4e342e",
    border: "none",
    padding: "10px 20px",
    borderRadius: "6px",
    cursor: "pointer",
    fontWeight: "bold",
    fontSize: "1rem",
  },
  mainLayout: {
    display: "flex",
    flexDirection: "column",
    gap: "30px",
  },
  tableContainer: {
    backgroundColor: "#fff",
    padding: "20px",
    borderRadius: "8px",
    boxShadow: "0 4px 6px rgba(0,0,0,0.05)",
    overflowX: "auto",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    marginTop: "15px",
  },
  tableHeader: {
    backgroundColor: "#f5f0eb",
    textAlign: "left",
    color: "#5c4033",
  },
  tableRow: {
    borderBottom: "1px solid #eee",
  },
  boldText: {
    fontWeight: "600",
  },
  badge: {
    backgroundColor: "#efebe9",
    color: "#5d4037",
    padding: "4px 8px",
    borderRadius: "4px",
    fontSize: "0.85rem",
  },
  actionBtn: {
    backgroundColor: "#e0f2f1",
    color: "#00695c",
    border: "none",
    padding: "6px 10px",
    borderRadius: "4px",
    cursor: "pointer",
    marginRight: "5px",
    fontSize: "0.85rem",
  },
  editBtn: {
    backgroundColor: "#fff9c4",
    color: "#f57f17",
    border: "none",
    padding: "6px 10px",
    borderRadius: "4px",
    cursor: "pointer",
    marginRight: "5px",
    fontSize: "0.85rem",
  },
  deleteBtn: {
    backgroundColor: "#ffebee",
    color: "#c62828",
    border: "none",
    padding: "6px 10px",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "0.85rem",
  },
  card: {
    backgroundColor: "#fff",
    padding: "20px",
    borderRadius: "8px",
    boxShadow: "0 4px 6px rgba(0,0,0,0.05)",
    borderLeft: "5px solid #8b5a2b",
  },
  closeCardBtn: {
    marginTop: "15px",
    backgroundColor: "#795548",
    color: "#fff",
    border: "none",
    padding: "6px 12px",
    borderRadius: "4px",
    cursor: "pointer",
  },
  modalOverlay: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0,0,0,0.5)",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 1000,
  },
  modalContent: {
    backgroundColor: "#fff",
    padding: "30px",
    borderRadius: "8px",
    width: "450px",
    maxWidth: "90%",
    boxShadow: "0 4px 15px rgba(0,0,0,0.2)",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "15px",
    marginTop: "15px",
  },
  formGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "5px",
  },
  input: {
    padding: "8px",
    borderRadius: "4px",
    border: "1px solid #ccc",
    fontSize: "1rem",
  },
  textarea: {
    padding: "8px",
    borderRadius: "4px",
    border: "1px solid #ccc",
    fontSize: "1rem",
    height: "80px",
  },
  modalActions: {
    display: "flex",
    gap: "10px",
    marginTop: "10px",
  },
  saveBtn: {
    backgroundColor: "#4caf50",
    color: "#fff",
    border: "none",
    padding: "10px",
    borderRadius: "4px",
    cursor: "pointer",
    flex: 1,
    fontWeight: "bold",
  },
  cancelBtn: {
    backgroundColor: "#f44336",
    color: "#fff",
    border: "none",
    padding: "10px",
    borderRadius: "4px",
    cursor: "pointer",
    flex: 1,
    fontWeight: "bold",
  },
};