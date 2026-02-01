import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowUp, ArrowDown, Minus } from "lucide-react";
import { useBackendBaseUrl } from "@/hooks/useBackendBaseUrl";

interface WeeklySummary {
  total_predictions: number;
  completed: number;
  correct: number;
  incorrect: number;
  success_rate: number;
  week_start: string;
  week_end: string;
}

interface WeeklyComparison {
  current_week: WeeklySummary;
  previous_week: {
    total_predictions: number;
    completed: number;
    correct: number;
    success_rate: number;
  };
  change: {
    success_rate_change: number;
    trend: string;
  };
}

export default function WeeklySummaryView() {
  const { apiBase, loading: baseLoading, error: baseError } = useBackendBaseUrl();
  const [comparison, setComparison] = useState<WeeklyComparison | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!apiBase) return;
    fetchWeeklySummary();
  }, [apiBase]);

  const fetchWeeklySummary = async () => {
    if (!apiBase) return;
    try {
      const response = await fetch(`${apiBase}/api/v1/weekly-summary/compare`);
      const data = await response.json();
      setComparison(data);
    } catch (error) {
      console.error("Error fetching weekly summary:", error);
    } finally {
      setLoading(false);
    }
  };

  if (baseLoading || loading) {
    return <div className="p-6">Φόρτωση...</div>;
  }
  if (baseError) {
    return <div className="p-6 text-destructive">Σφάλμα backend: {baseError}</div>;
  }

  if (!comparison) {
    return <div className="p-6">Δεν υπάρχουν διαθέσιμα δεδομένα</div>;
  }

  const { current_week, previous_week, change } = comparison;

  const getTrendIcon = () => {
    if (change.trend === "up") return <ArrowUp className="h-5 w-5 text-green-600" />;
    if (change.trend === "down") return <ArrowDown className="h-5 w-5 text-red-600" />;
    return <Minus className="h-5 w-5 text-gray-600" />;
  };

  const getTrendColor = () => {
    if (change.trend === "up") return "text-green-600";
    if (change.trend === "down") return "text-red-600";
    return "text-gray-600";
  };

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Εβδομαδιαία Σύνοψη</h2>

      {/* Current Week Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Προβλέψεις Εβδομάδας
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {current_week.total_predictions}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Σωστές
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">
              {current_week.correct}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Λάθος
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">
              {current_week.incorrect}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Ποσοστό Επιτυχίας
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {current_week.success_rate.toFixed(1)}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Comparison with Previous Week */}
      <Card>
        <CardHeader>
          <CardTitle>Σύγκριση με Προηγούμενη Εβδομάδα</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
              <div>
                <p className="text-sm text-muted-foreground">Ποσοστό Επιτυχίας</p>
                <p className="text-2xl font-bold">
                  Προηγούμενη: {previous_week.success_rate.toFixed(1)}%
                </p>
              </div>
              <div className="flex items-center gap-2">
                {getTrendIcon()}
                <span className={`text-2xl font-bold ${getTrendColor()}`}>
                  {Math.abs(change.success_rate_change).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">Τρέχουσα Εβδομάδα</p>
                <div className="space-y-1">
                  <p className="text-sm">Σύνολο: {current_week.total_predictions}</p>
                  <p className="text-sm text-green-600">Σωστές: {current_week.correct}</p>
                  <p className="text-sm text-red-600">Λάθος: {current_week.incorrect}</p>
                </div>
              </div>

              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">Προηγούμενη Εβδομάδα</p>
                <div className="space-y-1">
                  <p className="text-sm">Σύνολο: {previous_week.total_predictions}</p>
                  <p className="text-sm text-green-600">Σωστές: {previous_week.correct}</p>
                  <p className="text-sm">Ποσοστό: {previous_week.success_rate.toFixed(1)}%</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}