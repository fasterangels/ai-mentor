import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TrendingUp, TrendingDown } from "lucide-react";
import { useBackendBaseUrl } from "@/hooks/useBackendBaseUrl";

interface Statistics {
  id: number;
  market_type: string;
  total_predictions: number;
  correct_predictions: number;
  success_rate: number;
  last_updated: string;
}

export default function StatisticsView() {
  const { apiBase, loading: baseLoading, error: baseError } = useBackendBaseUrl();
  const [statistics, setStatistics] = useState<Statistics[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!apiBase) return;
    fetchStatistics();
  }, [apiBase]);

  const fetchStatistics = async () => {
    if (!apiBase) return;
    try {
      const response = await fetch(`${apiBase}/api/v1/statistics`);
      const data = await response.json();
      setStatistics(data);
    } catch (error) {
      console.error("Error fetching statistics:", error);
    } finally {
      setLoading(false);
    }
  };

  const overall = statistics.find(s => s.market_type === "Overall");
  const marketStats = statistics.filter(s => s.market_type !== "Overall");

  const getBestMarket = () => {
    if (marketStats.length === 0) return null;
    return marketStats.reduce((best, current) => 
      current.success_rate > best.success_rate ? current : best
    );
  };

  const getWorstMarket = () => {
    if (marketStats.length === 0) return null;
    return marketStats.reduce((worst, current) => 
      current.success_rate < worst.success_rate ? current : worst
    );
  };

  const best = getBestMarket();
  const worst = getWorstMarket();

  if (baseLoading || loading) {
    return <div className="p-6">Φόρτωση...</div>;
  }
  if (baseError) {
    return <div className="p-6 text-destructive">Σφάλμα backend: {baseError}</div>;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Overall Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Συνολικό Ποσοστό Επιτυχίας
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {overall?.success_rate.toFixed(1)}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Σύνολο Προβλέψεων
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {overall?.total_predictions || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Σωστές Προβλέψεις
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">
              {overall?.correct_predictions || 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Market Statistics Table */}
      <Card>
        <CardHeader>
          <CardTitle>Στατιστικά ανά Αγορά</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Αγορά</TableHead>
                <TableHead>Σύνολο</TableHead>
                <TableHead>Σωστές</TableHead>
                <TableHead>Ποσοστό Επιτυχίας</TableHead>
                <TableHead>Απόδοση</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {marketStats.map((stat) => (
                <TableRow key={stat.id}>
                  <TableCell className="font-medium">{stat.market_type}</TableCell>
                  <TableCell>{stat.total_predictions}</TableCell>
                  <TableCell className="text-green-600 font-semibold">
                    {stat.correct_predictions}
                  </TableCell>
                  <TableCell>
                    <span className="text-lg font-bold">
                      {stat.success_rate.toFixed(1)}%
                    </span>
                  </TableCell>
                  <TableCell>
                    {best && stat.market_type === best.market_type && (
                      <div className="flex items-center gap-1 text-green-600">
                        <TrendingUp className="h-4 w-4" />
                        <span className="text-sm font-medium">Καλύτερη</span>
                      </div>
                    )}
                    {worst && stat.market_type === worst.market_type && (
                      <div className="flex items-center gap-1 text-red-600">
                        <TrendingDown className="h-4 w-4" />
                        <span className="text-sm font-medium">Χειρότερη</span>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}