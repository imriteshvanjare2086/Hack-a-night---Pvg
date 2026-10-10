import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { scoped, selectedAudit } from "../../services/api";
import type { Page } from "../../services/api/v2";
import type { AuditFilters, ReviewStatus } from "../../types";
import { compactMoney } from "../../utils";
import {
  DataState,
  Pagination,
  RiskBadge,
  SearchField,
  Select,
  StatusBadge,
} from "../common/Common";

const statusMap: Record<string, ReviewStatus> = {
  "Needs Review": "NEEDS_REVIEW",
  "In Investigation": "IN_INVESTIGATION",
  "Verification Requested": "VERIFICATION_REQUESTED",
  Cleared: "CLEARED",
};
type Row = {
  cluster_id: string;
  size: number;
  risk_score: number;
  total_disbursed: number;
  status: string;
  mean_member_score?: number;
  flagged_member_fraction?: number;
  independent_indicator_count?: number;
  evidence: { indicator: string; contribution: number }[];
};
export function ServerClusterTable({
  compact = false,
  externalFilters = {},
}: {
  compact?: boolean;
  externalFilters?: AuditFilters;
}) {
  const [q, setQ] = useState("");
  const [risk, setRisk] = useState("");
  const [status, setStatus] = useState("");
  const [district, setDistrict] = useState("");
  const [scheme, setScheme] = useState("");
  const [sort, setSort] = useState("risk");
  const [page, setPage] = useState(1);
  const [minimum, setMin] = useState(0);
  const [maximum, setMax] = useState(100);
  const limit = compact ? 5 : 25;
  const data = useQuery({
    queryKey: [
      "cluster-page",
      selectedAudit(),
      q,
      risk,
      status,
      district,
      scheme,
      sort,
      page,
      minimum,
      maximum,
      externalFilters,
    ],
    queryFn: () =>
      scoped<Page<Row>>("/clusters", {
        q,
        risk_level: risk,
        status,
        district: externalFilters.district || district,
        scheme: externalFilters.scheme || scheme,
        sort,
        minimum,
        maximum,
        offset: (page - 1) * limit,
        limit,
      }),
  });
  return (
    <>
      <div className="table-tools">
        <SearchField
          value={q}
          onChange={(v) => {
            setQ(v);
            setPage(1);
          }}
          placeholder="Search cluster ID or risk indicator…"
        />
        <div className="table-filter-right">
          <Select
            label="Filter risk level"
            value={risk}
            onChange={(v) => {
              setRisk(v);
              setPage(1);
            }}
            options={["", "Critical", "High", "Medium", "Low"]}
          />
          <Select
            label="Filter review status"
            value={status}
            onChange={(v) => {
              setStatus(v);
              setPage(1);
            }}
            options={[
              "",
              "Needs Review",
              "In Investigation",
              "Verification Requested",
              "Cleared",
            ]}
          />
        </div>
      </div>
      {!compact && (
        <div className="filter-row secondary-filters">
          <label>
            District
            <input
              value={district}
              onChange={(e) => {
                setDistrict(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <label>
            Scheme
            <input
              value={scheme}
              onChange={(e) => {
                setScheme(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <Select
            label="Sort clusters"
            value={sort}
            onChange={(v) => {
              setSort(v);
              setPage(1);
            }}
            options={[
              { value: "risk", label: "Risk score" },
              { value: "amount", label: "Disbursement amount" },
              { value: "size", label: "Connected size" },
            ]}
          />
          <label>
            Minimum score
            <input
              type="number"
              min={0}
              max={maximum}
              value={minimum}
              onChange={(e) => {
                setMin(Number(e.target.value));
                setPage(1);
              }}
            />
          </label>
          <label>
            Maximum score
            <input
              type="number"
              min={minimum}
              max={100}
              value={maximum}
              onChange={(e) => {
                setMax(Number(e.target.value));
                setPage(1);
              }}
            />
          </label>
          <button
            className="text-button"
            type="button"
            onClick={() => {
              setQ("");
              setRisk("");
              setStatus("");
              setDistrict("");
              setScheme("");
              setSort("risk");
              setMin(0);
              setMax(100);
              setPage(1);
            }}
          >
            Reset filters
          </button>
        </div>
      )}
      <DataState
        loading={data.isPending}
        error={data.error}
        retry={() => data.refetch()}
        empty={data.data?.total === 0}
      >
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Cluster / contributing indicators</th>
                <th>Beneficiaries</th>
                <th>Disbursements</th>
                <th>Maximum priority</th>
                {!compact && <th>Community context</th>}
                <th>Review status</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {data.data?.items.map((c) => (
                <tr key={c.cluster_id}>
                  <td>
                    <Link
                      className="record-link"
                      to={"/clusters/" + c.cluster_id}
                    >
                      {c.cluster_id}
                      <span>Computed review group</span>
                    </Link>
                    <small className="table-subtext">
                      {[
                        ...new Set(
                          c.evidence
                            .filter((e) => e.contribution > 0)
                            .map((e) => e.indicator.replaceAll("_", " ")),
                        ),
                      ].join(", ")}
                    </small>
                  </td>
                  <td>{c.size} connected</td>
                  <td>{compactMoney(c.total_disbursed)}</td>
                  <td>
                    <RiskBadge score={c.risk_score} />
                  </td>
                  {!compact && (
                    <td>
                      Mean {c.mean_member_score ?? "—"} ·{" "}
                      {c.flagged_member_fraction == null
                        ? "—"
                        : Math.round(c.flagged_member_fraction * 100) +
                          "%"}{" "}
                      flagged · {c.independent_indicator_count ?? "—"} indicator
                      types
                    </td>
                  )}
                  <td>
                    <StatusBadge
                      status={statusMap[c.status] || "NEEDS_REVIEW"}
                    />
                  </td>
                  <td>
                    <Link
                      className="row-action"
                      aria-label={`Open ${c.cluster_id}`}
                      to={"/clusters/" + c.cluster_id}
                    >
                      <ArrowRight size={17} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataState>
      <Pagination
        page={page}
        setPage={setPage}
        total={data.data?.total || 0}
        size={limit}
      />
      <p className="table-note">
        Disbursements cover all awards of connected members. Maximum score is an
        individual review index; community membership does not establish
        wrongdoing.
      </p>
    </>
  );
}
