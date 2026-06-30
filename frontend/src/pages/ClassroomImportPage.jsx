import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";

export default function ClassroomImportPage() {

  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState("");
  const [coursework, setCoursework] = useState([]);
  const [selectedItemIds, setSelectedItemIds] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [importing, setImporting] = useState(false);

  // Load courses on component mount
  useEffect(() => {
    setLoading(true);
    client
      .get("/classroom/courses")
      .then((res) => {
        setCourses(res.data);
        if (res.data.length > 0) {
          setSelectedCourseId(res.data[0].id);
        }
      })
      .catch((e) => {
        const detail = e.response?.data?.detail || "Make sure you connect Google Classroom under Settings.";
        setErrorMsg(`Failed to load courses: ${detail}`);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  // Fetch coursework when selected course changes
  useEffect(() => {
    if (!selectedCourseId) return;
    setLoading(true);
    setCoursework([]);
    setSelectedItemIds(new Set());
    setErrorMsg("");

    client
      .get(`/classroom/courses/${selectedCourseId}/coursework`)
      .then((res) => {
        setCoursework(res.data);
      })
      .catch((e) => {
        setErrorMsg("Failed to load assignments for this course.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [selectedCourseId]);

  const handleToggleSelectItem = (id) => {
    const next = new Set(selectedItemIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedItemIds(next);
  };

  const handleToggleSelectAll = () => {
    if (selectedItemIds.size === coursework.length) {
      setSelectedItemIds(new Set());
    } else {
      setSelectedItemIds(new Set(coursework.map((c) => c.id)));
    }
  };

  const handleImport = async () => {
    if (selectedItemIds.size === 0) return;
    setImporting(true);
    setErrorMsg("");

    const itemsToImport = coursework.filter((c) => selectedItemIds.has(c.id));

    try {
      await client.post("/classroom/import", { items: itemsToImport });
      navigate("/");
    } catch (e) {
      setErrorMsg("Failed to import selected assignments.");
      setImporting(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "No due date";
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="max-w-4xl mx-auto p-6 classroom-import-page">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-extrabold text-[var(--color-text)]">Import Classroom Work</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">
            Choose a course to load your assignments and select which ones to add to LifeSaver.
          </p>
        </div>
        {courses.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-[var(--color-text-secondary)] whitespace-nowrap">Course:</span>
            <select
              value={selectedCourseId}
              onChange={(e) => setSelectedCourseId(e.target.value)}
              className="bg-[var(--color-surface)] border border-[var(--color-border)] text-sm rounded-[var(--radius-md)] px-4 py-2 text-[var(--color-text)] focus:border-[var(--color-accent)] outline-none min-w-[200px]"
            >
              {courses.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.name} {course.section ? `(${course.section})` : ""}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {errorMsg && (
        <div className="p-4 bg-red-950/20 border border-red-800/40 text-red-300 rounded-[var(--radius-md)] text-sm font-semibold mb-6">
          {errorMsg}
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center p-12">
          <div className="loading-spinner mb-4"></div>
          <p className="text-[var(--color-text-secondary)] text-sm font-medium">Fetching Google Classroom details...</p>
        </div>
      ) : coursework.length === 0 ? (
        <div className="text-center py-16 bg-[var(--color-surface)] border border-dashed border-[var(--color-border)] rounded-[var(--radius-lg)]">
          <span className="text-4xl mb-3 block">📚</span>
          <h3 className="text-lg font-bold text-[var(--color-text)] mb-1">No assignments found</h3>
          <p className="text-[var(--color-text-secondary)] text-xs max-w-sm mx-auto leading-relaxed">
            There are no coursework items listed in this Google Classroom course, or all have been fetched.
          </p>
        </div>
      ) : (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] shadow-md overflow-hidden">
          {/* Header Row */}
          <div className="flex items-center justify-between p-4 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)]">
            <button
              onClick={handleToggleSelectAll}
              className="flex items-center gap-2 text-xs font-bold text-[var(--color-accent)] uppercase tracking-wider hover:underline bg-none border-none cursor-pointer"
            >
              {selectedItemIds.size === coursework.length ? "Deselect All" : "Select All"}
            </button>
            <span className="text-xs text-[var(--color-text-secondary)] font-semibold">
              {selectedItemIds.size} of {coursework.length} selected
            </span>
          </div>

          {/* Coursework List */}
          <div className="divide-y divide-[var(--color-border)]">
            {coursework.map((item) => {
              const isChecked = selectedItemIds.has(item.id);
              return (
                <div
                  key={item.id}
                  onClick={() => handleToggleSelectItem(item.id)}
                  className={`flex gap-4 p-5 hover:bg-[var(--color-bg-secondary)] transition-colors cursor-pointer ${
                    isChecked ? "bg-[var(--color-bg-secondary)]/50" : ""
                  }`}
                >
                  {/* Checkbox */}
                  <div className="flex items-start pt-1">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => {}} // toggled by outer click handler
                      className="w-5 h-5 rounded-[var(--radius-sm)] accent-[var(--color-accent)] border-[var(--color-border)]"
                    />
                  </div>

                  {/* Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-1 mb-2">
                      <h3 className="font-bold text-[var(--color-text)] text-sm sm:text-base leading-snug">{item.title}</h3>
                      <span
                        className={`text-xs font-semibold px-2.5 py-1 rounded-full whitespace-nowrap self-start ${
                          item.due_date
                            ? "bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]"
                            : "bg-amber-950/20 text-amber-300 border border-amber-800/40"
                        }`}
                      >
                        📅 {formatDate(item.due_date)}
                      </span>
                    </div>

                    {item.description && (
                      <p className="text-[var(--color-text-secondary)] text-xs leading-relaxed line-clamp-3 mb-3">
                        {item.description}
                      </p>
                    )}

                    {item.materials.length > 0 && (
                      <div className="flex flex-wrap gap-2 items-center">
                        <span className="text-[10px] font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                          Resources:
                        </span>
                        {item.materials.map((m, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)] rounded-[var(--radius-sm)] border border-[var(--color-border)]"
                          >
                            📎 {m.title}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Import Footer Actions */}
          <div className="p-4 bg-[var(--color-bg-secondary)] border-t border-[var(--color-border)] flex justify-end gap-3">
            <button className="btn btn-ghost" onClick={() => navigate("/")} disabled={importing}>
              Cancel
            </button>
            <button
              className="btn btn-primary px-6"
              onClick={handleImport}
              disabled={selectedItemIds.size === 0 || importing}
            >
              {importing ? "Importing Assignments..." : `Import Selected (${selectedItemIds.size})`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
