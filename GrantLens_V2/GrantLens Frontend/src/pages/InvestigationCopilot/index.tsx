import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  Download,
  FileCheck,
  FileText,
  HelpCircle,
  ListFilter,
  Save,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  DataState,
  PageHeading,
  Panel,
  RiskBadge,
  useToast,
} from "../../components/common/Common";
import { copilotApi } from "../../services/api";
import type {
  InvestigationQuestionItem,
  QuestionPriority,
  QuestionStatus,
} from "../../types";

export function InvestigationCopilot() {
  const { id = "CASE-BEN-000037" } = useParams();
  const toast = useToast();
  const queryClient = useQueryClient();

  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [generalNotes, setGeneralNotes] = useState<string>("");
  const [investigationStatus, setInvestigationStatus] = useState<string>("Under Review");
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  const q = useQuery({
    queryKey: ["copilot-investigation", id],
    queryFn: () => copilotApi.getInvestigation(id),
  });

  const invData = q.data?.investigation;
  const caseData = q.data?.case;
  const questions = q.data?.questions || [];

  useEffect(() => {
    if (invData) {
      setGeneralNotes(invData.notes || "");
      setInvestigationStatus(invData.status || "Under Review");
    }
  }, [invData?.investigation_id, invData?.notes, invData?.status]);

  // Mutation to update general investigation notes
  const updateInvMutation = useMutation({
    mutationFn: (vars: { notes: string; status: string }) =>
      copilotApi.updateInvestigationNotes(invData!.investigation_id, vars.notes, vars.status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["copilot-investigation", id] });
      toast("Investigation observations saved successfully.");
    },
    onError: () => {
      toast("Failed to save observations. Please try again.");
    },
  });

  // Mutation to update question status or notes
  const updateQuestionMutation = useMutation({
    mutationFn: (vars: {
      questionId: string;
      patch: { status?: string; officer_notes?: string };
    }) =>
      copilotApi.updateQuestion(invData!.investigation_id, vars.questionId, vars.patch),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["copilot-investigation", id] });
      toast("Question record updated.");
    },
  });

  const handleDownloadPdf = async () => {
    if (!invData) return;
    try {
      setIsDownloadingPdf(true);
      const url = copilotApi.pdfUrl(invData.investigation_id);
      const res = await fetch(url);
      if (!res.ok) throw new Error("PDF download failed");
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = `investigation-${id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
      toast("Investigation PDF downloaded successfully.");
    } catch {
      toast("Error generating PDF report. Please try again.");
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const categories = [
    "All",
    ...Array.from(new Set(questions.map((item) => item.category))),
  ];

  const filteredQuestions =
    selectedCategory === "All"
      ? questions
      : questions.filter((item) => item.category === selectedCategory);

  const unresolvedCount = questions.filter(
    (item) => item.status === "Pending" || item.status === "Needs Follow-up",
  ).length;

  const verifiedCount = questions.filter(
    (item) => item.status === "Verified",
  ).length;

  return (
    <div className="copilot-container">
      <Link className="back-link" to={`/clusters/${id}`}>
        <ArrowLeft size={14} /> Back to Case Overview ({id})
      </Link>

      <PageHeading
        eyebrow="GHOSTAUDIT INVESTIGATION COPILOT"
        title={`Investigation Workspace · ${id}`}
        description="Structured forensic checklist, evidence verification prompts, and officer notes."
      >
        <button
          className="button primary"
          disabled={!invData || isDownloadingPdf}
          onClick={handleDownloadPdf}
        >
          <Download size={16} />
          {isDownloadingPdf ? "Generating PDF…" : "Generate Investigation PDF"}
        </button>
      </PageHeading>

      <div className="copilot-banner">
        <Sparkles size={18} className="copilot-banner-icon" />
        <div>
          <strong>Investigative Principle:</strong> Fraud detection is not the end of an investigation.
          The right questions help officers verify evidence and decide what to investigate next. A risk
          score is an inquiry priority index, not proof of guilt.
        </div>
      </div>

      <DataState
        loading={q.isPending}
        error={q.error}
        empty={!caseData}
        retry={() => q.refetch()}
      >
        {caseData && invData && (
          <>
            {/* SECTION A: CASE SUMMARY */}
            <div className="copilot-summary-grid">
              <Panel title="Case Summary" className="copilot-summary-panel">
                <div className="copilot-meta-row">
                  <div>
                    <span className="muted small">Case Reference</span>
                    <h3>{caseData.case_id || id}</h3>
                  </div>
                  <div>
                    <span className="muted small">Scheme</span>
                    <p className="font-semibold">
                      {(caseData.schemes && caseData.schemes.join(", ")) ||
                        caseData.scheme ||
                        "Scholarship Scheme"}
                    </p>
                  </div>
                  <div>
                    <span className="muted small">Investigation Status</span>
                    <div>
                      <span className="copilot-status-badge under-review">
                        {investigationStatus}
                      </span>
                    </div>
                  </div>
                  <div>
                    <span className="muted small">Review Priority</span>
                    <div>
                      <RiskBadge score={caseData.risk_score || 0} />
                    </div>
                  </div>
                </div>

                <div className="copilot-counts-row">
                  <div className="count-pill">
                    <strong>{caseData.beneficiary_ids?.length || 1}</strong>
                    <span>Linked Beneficiaries</span>
                  </div>
                  <div className="count-pill">
                    <strong>{caseData.evidence?.length || 0}</strong>
                    <span>Flagged Evidence Items</span>
                  </div>
                  <div className="count-pill">
                    <strong>{questions.length}</strong>
                    <span>Generated Questions</span>
                  </div>
                  <div className="count-pill">
                    <strong style={{ color: unresolvedCount > 0 ? "#b45309" : "#15803d" }}>
                      {unresolvedCount}
                    </strong>
                    <span>Unresolved Prompts</span>
                  </div>
                </div>
              </Panel>

              {/* SECTION B: DETECTED SIGNALS SUMMARY */}
              <Panel title="Forensic Signals & Evidence" className="copilot-evidence-panel">
                <div className="copilot-evidence-list">
                  {(caseData.evidence || []).length === 0 ? (
                    <p className="muted">No automated signal evidence recorded for this case.</p>
                  ) : (
                    (caseData.evidence || []).map((ev: any, idx: number) => (
                      <div className="evidence-badge-item" key={idx}>
                        <div className="evidence-header">
                          <span className="evidence-name">
                            <ShieldAlert size={14} />
                            {(ev.indicator || "Signal").replaceAll("_", " ").toUpperCase()}
                          </span>
                          <span className="evidence-points">+{ev.contribution || 0} pts</span>
                        </div>
                        <p className="evidence-desc">{ev.explanation}</p>
                        {ev.source_record_ids && ev.source_record_ids.length > 0 && (
                          <div className="evidence-refs">
                            <span className="muted small">Records: </span>
                            {ev.source_record_ids.slice(0, 4).map((r: string) => (
                              <code key={r}>{r}</code>
                            ))}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </Panel>
            </div>

            {/* UNRESOLVED NOTICE */}
            {unresolvedCount > 0 && (
              <div className="copilot-unresolved-banner">
                <AlertTriangle size={18} />
                <span>
                  <strong>{unresolvedCount} verification questions require officer action.</strong> Complete
                  field verifications before finalizing investigation conclusions.
                </span>
                <span className="badge-count">{verifiedCount} of {questions.length} Verified</span>
              </div>
            )}

            {/* SECTION C & D: EVIDENCE-LINKED INVESTIGATION QUESTIONS */}
            <Panel
              title="Evidence-Linked Investigation Checklist"
              action={
                <span className="muted small">
                  {filteredQuestions.length} of {questions.length} questions displayed
                </span>
              }
            >
              <div className="category-tabs">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    className={`category-tab ${selectedCategory === cat ? "active" : ""}`}
                    onClick={() => setSelectedCategory(cat)}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              <div className="questions-container">
                {filteredQuestions.map((qItem) => (
                  <QuestionCard
                    key={qItem.question_id}
                    question={qItem}
                    onUpdate={(patch) =>
                      updateQuestionMutation.mutate({
                        questionId: qItem.question_id,
                        patch,
                      })
                    }
                  />
                ))}
              </div>
            </Panel>

            {/* SECTION E: GENERAL CASE OBSERVATIONS & DISPOSITION */}
            <Panel title="Officer Observations & Next Steps">
              <div className="copilot-notes-section">
                <label>
                  <span>General Case Notes and Verification Observations</span>
                  <textarea
                    rows={4}
                    placeholder="Enter overall observations, findings from institutional inquiries, or justification for resolution…"
                    value={generalNotes}
                    onChange={(e) => setGeneralNotes(e.target.value)}
                  />
                </label>

                <div className="copilot-footer-actions">
                  <div className="status-selector">
                    <span>Investigation Disposition:</span>
                    <select
                      value={investigationStatus}
                      onChange={(e) => setInvestigationStatus(e.target.value)}
                    >
                      <option value="Under Review">Under Review</option>
                      <option value="In Progress">In Progress</option>
                      <option value="Completed">Completed</option>
                      <option value="Escalated">Escalated to Vigilance</option>
                    </select>
                  </div>

                  <button
                    className="button primary"
                    disabled={updateInvMutation.isPending}
                    onClick={() =>
                      updateInvMutation.mutate({
                        notes: generalNotes,
                        status: investigationStatus,
                      })
                    }
                  >
                    <Save size={15} />
                    {updateInvMutation.isPending ? "Saving…" : "Save Observations"}
                  </button>
                </div>
              </div>
            </Panel>
          </>
        )}
      </DataState>
    </div>
  );
}

function QuestionCard({
  question,
  onUpdate,
}: {
  question: InvestigationQuestionItem;
  onUpdate: (patch: { status?: string; officer_notes?: string }) => void;
}) {
  const [notes, setNotes] = useState(question.officer_notes || "");
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    setNotes(question.officer_notes || "");
    setDirty(false);
  }, [question.officer_notes]);

  const priorityColor: Record<QuestionPriority, string> = {
    High: "#b91c1c",
    Medium: "#b45309",
    Low: "#2563eb",
  };

  return (
    <div className={`question-card priority-${question.priority.toLowerCase()}`}>
      <div className="question-header">
        <div className="question-id-tags">
          <span className="question-id-badge">{question.question_id}</span>
          <span
            className="priority-pill"
            style={{ color: priorityColor[question.priority] }}
          >
            {question.priority} Priority
          </span>
          <span className="category-pill">{question.category}</span>
        </div>

        <div className="question-status-control">
          <label>
            <span className="muted small">Status:</span>
            <select
              value={question.status}
              onChange={(e) =>
                onUpdate({ status: e.target.value as QuestionStatus })
              }
            >
              <option value="Pending">Pending</option>
              <option value="Verified">Verified</option>
              <option value="Needs Follow-up">Needs Follow-up</option>
              <option value="Not Applicable">Not Applicable</option>
            </select>
          </label>
        </div>
      </div>

      <h3 className="question-prompt">{question.question_text}</h3>

      <div className="question-context-box">
        <div className="context-item">
          <strong>Why ask this:</strong>
          <p>{question.rationale}</p>
        </div>
        <div className="context-item">
          <strong>Verification action:</strong>
          <p>{question.verification_action}</p>
        </div>
      </div>

      {question.evidence_refs && question.evidence_refs.length > 0 && (
        <div className="question-refs">
          <span className="muted small">Triggering Evidence:</span>
          {question.evidence_refs.map((ref) => (
            <code key={ref}>{ref}</code>
          ))}
        </div>
      )}

      <div className="question-notes-input">
        <label>
          <span>Officer Notes / Findings</span>
          <div className="notes-input-wrapper">
            <input
              type="text"
              placeholder="Record verification response, source reference, or inquiry findings…"
              value={notes}
              onChange={(e) => {
                setNotes(e.target.value);
                setDirty(true);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && dirty) {
                  onUpdate({ officer_notes: notes });
                  setDirty(false);
                }
              }}
            />
            {dirty && (
              <button
                type="button"
                className="button small"
                onClick={() => {
                  onUpdate({ officer_notes: notes });
                  setDirty(false);
                }}
              >
                Save
              </button>
            )}
          </div>
        </label>
      </div>

      <div className="question-card-footer">
        <span className="muted small">
          Last updated: {new Date(question.updated_at).toLocaleDateString("en-IN")} by{" "}
          {question.updated_by}
        </span>
      </div>
    </div>
  );
}
