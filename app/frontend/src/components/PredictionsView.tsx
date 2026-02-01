import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Eye } from "lucide-react";
import { useBackendBaseUrl } from "@/hooks/useBackendBaseUrl";

interface Prediction {
  id: number;
  match_id: string;
  home_team: string;
  away_team: string;
  prediction_date: string;
  match_date: string | null;
  market_1x2: string | null;
  market_1x2_probability: number | null;
  market_over_under: string | null;
  market_over_under_probability: number | null;
  market_gg_nogg: string | null;
  market_gg_nogg_probability: number | null;
  status: string;
}

export default function PredictionsView() {
  const { apiBase, loading: baseLoading, error: baseError } = useBackendBaseUrl();
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!apiBase) return;
    fetchPredictions();
  }, [apiBase]);

  const fetchPredictions = async () => {
    if (!apiBase) return;
    try {
      const response = await fetch(`${apiBase}/api/v1/predictions`);
      const data = await response.json();
      setPredictions(data);
    } catch (error) {
      console.error("Error fetching predictions:", error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleDateString("el-GR");
  };

  if (baseLoading || loading) {
    return <div className="p-6">Φόρτωση...</div>;
  }
  if (baseError) {
    return <div className="p-6 text-destructive">Σφάλμα backend: {baseError}</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Προβλέψεις Αγώνων</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Αγώνας</TableHead>
                <TableHead>1X2</TableHead>
                <TableHead>Over/Under</TableHead>
                <TableHead>GG/NoGG</TableHead>
                <TableHead>Ημερομηνία</TableHead>
                <TableHead>Κατάσταση</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {predictions.map((pred) => (
                <TableRow key={pred.id}>
                  <TableCell className="font-medium">
                    {pred.home_team} vs {pred.away_team}
                  </TableCell>
                  <TableCell>
                    {pred.market_1x2 && (
                      <div className="flex flex-col">
                        <span className="font-semibold">{pred.market_1x2}</span>
                        <span className="text-xs text-muted-foreground">
                          {pred.market_1x2_probability?.toFixed(1)}%
                        </span>
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    {pred.market_over_under && (
                      <div className="flex flex-col">
                        <span className="font-semibold">{pred.market_over_under}</span>
                        <span className="text-xs text-muted-foreground">
                          {pred.market_over_under_probability?.toFixed(1)}%
                        </span>
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    {pred.market_gg_nogg && (
                      <div className="flex flex-col">
                        <span className="font-semibold">{pred.market_gg_nogg}</span>
                        <span className="text-xs text-muted-foreground">
                          {pred.market_gg_nogg_probability?.toFixed(1)}%
                        </span>
                      </div>
                    )}
                  </TableCell>
                  <TableCell>{formatDate(pred.match_date)}</TableCell>
                  <TableCell>
                    <Badge variant={pred.status === "pending" ? "secondary" : "default"}>
                      {pred.status === "pending" ? "Εκκρεμεί" : "Ολοκληρώθηκε"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm">
                      <Eye className="h-4 w-4" />
                    </Button>
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