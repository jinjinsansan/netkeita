"use client";

import { useState, useEffect } from "react";
import { fetchRaces, getAvailableDates } from "@/lib/api";
import type { RaceSummary } from "@/lib/types";
import Link from "next/link";

function dateLabel(d: string): string {
  const dt = new Date(`${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`);
  const days = ["日", "月", "火", "水", "木", "金", "土"];
  return `${dt.getMonth() + 1}/${dt.getDate()}(${days[dt.getDay()]})`;
}

export default function Home() {
  const mockDates = getAvailableDates();
  const dates = mockDates.length > 0 ? mockDates : ["20260329"];
  const [selectedDate, setSelectedDate] = useState(dates[0]);
  const [venues, setVenues] = useState<{ venue: string; races: RaceSummary[] }[]>([]);
  const [selectedVenue, setSelectedVenue] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchRaces(selectedDate).then((data) => {
      setVenues(data.venues);
      if (data.venues.length > 0) {
        setSelectedVenue((prev) =>
          data.venues.find((v) => v.venue === prev) ? prev : data.venues[0].venue
        );
      } else {
        setSelectedVenue("");
      }
      setLoading(false);
    });
  }, [selectedDate]);

  const currentRaces = venues.find((v) => v.venue === selectedVenue)?.races || [];

  return (
    <div className="max-w-[960px] mx-auto px-3 py-4">
      {/* Date tabs */}
      <div className="flex items-center gap-1 mb-2 border-b border-[#c6c9d3] pb-2">
        {dates.map((d) => (
          <button
            key={d}
            onClick={() => setSelectedDate(d)}
            className={`px-3 py-1 text-xs font-bold rounded-t border border-b-0 transition ${
              selectedDate === d
                ? "bg-[#1f7a1f] text-white border-[#1f7a1f]"
                : "bg-[#f0f0f0] text-[#555] border-[#ccc] hover:bg-[#e8e8e8]"
            }`}
          >
            {dateLabel(d)}
          </button>
        ))}
      </div>

      {/* Venue tabs */}
      {venues.length > 0 && (
        <div className="flex items-center gap-0 mb-3">
          {venues.map((v) => (
            <button
              key={v.venue}
              onClick={() => setSelectedVenue(v.venue)}
              className={`px-4 py-1.5 text-xs font-bold border transition ${
                selectedVenue === v.venue
                  ? "bg-[#1f7a1f] text-white border-[#1f7a1f]"
                  : "bg-white text-[#333] border-[#c6c9d3] hover:bg-[#f5f5f5]"
              }`}
            >
              {v.venue}
            </button>
          ))}
        </div>
      )}

      {/* Race number tiles (netkeiba style) */}
      {loading ? (
        <p className="text-[#888] text-xs py-6 text-center">読み込み中...</p>
      ) : currentRaces.length > 0 ? (
        <>
          <div className="flex flex-wrap gap-1 mb-4">
            {currentRaces.map((race) => (
              <Link
                key={race.race_id}
                href={`/race/${encodeURIComponent(race.race_id)}`}
                className="flex flex-col items-center justify-center w-[72px] h-[52px] border border-[#c6c9d3] rounded bg-white hover:bg-[#f0f4ff] transition text-center"
              >
                <span className="text-sm font-bold text-[#1f7a1f]">{race.race_number}R</span>
                <span className="text-[10px] text-[#888] truncate max-w-[68px] leading-tight">
                  {race.race_name}
                </span>
              </Link>
            ))}
          </div>

          {/* Race list table */}
          <table className="nk-table">
            <thead>
              <tr>
                <th className="w-10">R</th>
                <th>レース名</th>
                <th className="w-20">距離</th>
                <th className="w-12">頭数</th>
                <th className="w-14">発走</th>
              </tr>
            </thead>
            <tbody>
              {currentRaces.map((race) => (
                <tr key={race.race_id}>
                  <td className="text-center font-bold text-[#1f7a1f]">{race.race_number}</td>
                  <td>
                    <Link
                      href={`/race/${encodeURIComponent(race.race_id)}`}
                      className="text-[#1E88E5] hover:underline font-medium"
                    >
                      {race.race_name}
                    </Link>
                  </td>
                  <td className="text-center text-[#555]">{race.distance}</td>
                  <td className="text-center">{race.headcount}</td>
                  <td className="text-center text-[#888]">{race.start_time || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <p className="text-[#888] text-xs py-6 text-center">
          この日のレースデータはまだありません
        </p>
      )}
    </div>
  );
}
