import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

export default function MatchHistoryView() {
  // Mock data - in real app, fetch from API
  const recentResults = [
    { date: "2024-01-20", match: "Manchester United vs Liverpool", score: "2-1", result: "W" },
    { date: "2024-01-18", match: "Barcelona vs Real Madrid", score: "1-1", result: "D" },
    { date: "2024-01-15", match: "Bayern vs Dortmund", score: "3-2", result: "W" },
  ];

  const headToHead = [
    { date: "2023-12-10", match: "Manchester United vs Liverpool", score: "0-2", result: "L" },
    { date: "2023-09-15", match: "Liverpool vs Manchester United", score: "1-1", result: "D" },
    { date: "2023-05-20", match: "Manchester United vs Liverpool", score: "2-0", result: "W" },
  ];

  const getResultBadge = (result: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive"> = {
      W: "default",
      D: "secondary",
      L: "destructive"
    };
    const colors: Record<string, string> = {
      W: "bg-green-500",
      D: "bg-yellow-500",
      L: "bg-red-500"
    };
    
    return (
      <Badge variant={variants[result]} className={colors[result]}>
        {result}
      </Badge>
    );
  };

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Ιστορικό Αγώνων</h2>

      <Tabs defaultValue="recent" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="recent">Πρόσφατα Αποτελέσματα</TabsTrigger>
          <TabsTrigger value="h2h">Head-to-Head</TabsTrigger>
          <TabsTrigger value="form">Φόρμα</TabsTrigger>
        </TabsList>

        <TabsContent value="recent">
          <Card>
            <CardHeader>
              <CardTitle>Πρόσφατα Αποτελέσματα</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ημερομηνία</TableHead>
                    <TableHead>Αγώνας</TableHead>
                    <TableHead>Σκορ</TableHead>
                    <TableHead>Αποτέλεσμα</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentResults.map((match, idx) => (
                    <TableRow key={idx}>
                      <TableCell>{match.date}</TableCell>
                      <TableCell className="font-medium">{match.match}</TableCell>
                      <TableCell className="font-bold">{match.score}</TableCell>
                      <TableCell>{getResultBadge(match.result)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="h2h">
          <Card>
            <CardHeader>
              <CardTitle>Προηγούμενες Αναμετρήσεις</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ημερομηνία</TableHead>
                    <TableHead>Αγώνας</TableHead>
                    <TableHead>Σκορ</TableHead>
                    <TableHead>Αποτέλεσμα</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {headToHead.map((match, idx) => (
                    <TableRow key={idx}>
                      <TableCell>{match.date}</TableCell>
                      <TableCell className="font-medium">{match.match}</TableCell>
                      <TableCell className="font-bold">{match.score}</TableCell>
                      <TableCell>{getResultBadge(match.result)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="form">
          <Card>
            <CardHeader>
              <CardTitle>Φόρμα Ομάδων</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <span className="font-semibold">Manchester United</span>
                  <div className="flex gap-1">
                    {["W", "W", "D", "L", "W"].map((r, i) => (
                      <div key={i} className="w-8 h-8 flex items-center justify-center">
                        {getResultBadge(r)}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <span className="font-semibold">Liverpool</span>
                  <div className="flex gap-1">
                    {["W", "D", "W", "W", "L"].map((r, i) => (
                      <div key={i} className="w-8 h-8 flex items-center justify-center">
                        {getResultBadge(r)}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}